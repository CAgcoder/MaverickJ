"""Tier-1 baseline data load + deterministic tool runs (no LLM)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState
from maverickj.schemas.supply_chain_engine import SupplyChainConfig
from maverickj.supply_chain.data.data_loader import init_db
from maverickj.supply_chain.paths import resolve_supply_chain_paths
from maverickj.supply_chain.tools.eoq import calc_eoq
from maverickj.supply_chain.tools.erp import get_forecast, get_full_snapshot
from maverickj.supply_chain.tools.events import query_active_events
from maverickj.supply_chain.tools.market_data import fetch_and_cache, fetch_cached
from maverickj.supply_chain.tools.monte_carlo import run_monte_carlo
from maverickj.supply_chain.tools.registry import ToolCallRegistry
from maverickj.supply_chain.tools.tco import calc_tco

logger = logging.getLogger(__name__)

_DEFAULT_SKU = "SKU-A21"


def _guess_sku(question: str) -> str:
    m = re.search(r"(SKU-[A-Z0-9-]+)", question, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return _DEFAULT_SKU


async def data_warmup_node(state: DebateState, router: ModelRouter) -> dict[str, Any]:
    """Pre-compute ERP / events / market + baseline EOQ / MC / TCO; write tool_calls + data_pack."""
    _ = router
    sc = state.supply_chain_config or SupplyChainConfig()
    db_s, events_s, market_s = resolve_supply_chain_paths(sc)
    db_path = Path(db_s)
    events_path = Path(events_s)
    market_cache_path = Path(market_s)
    base = db_path.parent

    tool_calls: dict[str, Any] = dict(state.tool_calls)
    registry = ToolCallRegistry(tool_calls)
    rnd = state.current_round or 1
    invoked_by = "data_warmup"
    source = "warmup"

    init_db(str(db_path))
    registry.record(
        tool_name="init_db",
        inputs={"db_path": str(db_path)},
        outputs={"ok": True},
        summary="SQLite schema + seed applied",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    erp_snapshot = get_full_snapshot(str(db_path))
    registry.record(
        tool_name="get_full_snapshot",
        inputs={"db_path": str(db_path)},
        outputs={"keys": list(erp_snapshot.keys()), "sku_count": len(erp_snapshot.get("inventory", []))},
        summary="ERP snapshot (inventory, suppliers, forecast)",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    events = query_active_events(events_path=str(events_path))
    registry.record(
        tool_name="query_active_events",
        inputs={"events_path": str(events_path)},
        outputs={"count": len(events)},
        summary=f"{len(events)} active supply-chain events",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    market_payload: dict[str, Any]
    try:
        market_payload = fetch_and_cache(
            tickers=list(sc.market_data.tickers),
            cache_path=str(market_cache_path),
            cache_ttl_hours=sc.market_data.cache_ttl_hours,
            offline_mode=sc.market_data.offline_mode,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("market fetch failed, using cache only: %s", exc)
        market_payload = fetch_cached(str(market_cache_path))
    registry.record(
        tool_name="fetch_market_data",
        inputs={"tickers": sc.market_data.tickers, "offline": sc.market_data.offline_mode},
        outputs={"fetched_at": market_payload.get("fetched_at"), "symbols": list(market_payload.get("data", {}).keys())},
        summary="Market data (yfinance or cache)",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    sku = _guess_sku(state.question)
    inv_row = next((r for r in erp_snapshot["inventory"] if r["sku"] == sku), erp_snapshot["inventory"][0])
    forecasts = get_forecast(str(db_path), sku)
    if not forecasts:
        raise RuntimeError(f"No forecast rows for {sku}")
    w1 = forecasts[0]
    annual_demand = float(w1["mean_demand"]) * 52
    setup_cost = float(inv_row["setup_cost_per_order"])
    holding = float(inv_row["holding_cost_per_unit_year"])

    eoq_out = calc_eoq(demand=annual_demand, setup_cost=setup_cost, holding_cost=holding)
    registry.record(
        tool_name="calc_eoq",
        inputs={"sku": sku, "annual_demand": annual_demand, "setup_cost": setup_cost, "holding_cost": holding},
        outputs=eoq_out,
        summary=f"EOQ baseline for {sku}",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    sims = sc.monte_carlo.simulations
    mc_out = run_monte_carlo(mean=float(w1["mean_demand"]), std_dev=float(w1["std_dev"]), simulations=sims)
    registry.record(
        tool_name="run_monte_carlo",
        inputs={"sku": sku, "mean": w1["mean_demand"], "std_dev": w1["std_dev"], "simulations": sims},
        outputs=mc_out,
        summary=f"Monte Carlo demand risk ({sims} sims) for {sku}",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    suppliers = {s["supplier_id"]: s for s in erp_snapshot["suppliers"]}
    local = suppliers.get("SUP-LOCAL-01")
    sea = suppliers.get("SUP-SEA-03")
    if not local or not sea:
        raise RuntimeError("Seed DB must include SUP-LOCAL-01 and SUP-SEA-03")

    def _tco_row(s: dict[str, Any], tariff: float, freight_factor: float) -> dict[str, Any]:
        up = float(s["unit_price"])
        return calc_tco(
            unit_price=up,
            freight=up * freight_factor,
            tariff=up * tariff,
            capital_cost=up * 0.005,
            defect_rate=float(s["defect_rate"]),
            quantity=1000.0,
            rework_cost_per_defect=12.0,
        )

    tco_local = _tco_row(local, tariff=0.0, freight_factor=0.04)
    tco_sea = _tco_row(sea, tariff=0.05, freight_factor=0.12)
    registry.record(
        tool_name="calc_tco",
        inputs={"path": "local", "supplier": "SUP-LOCAL-01", "quantity": 1000},
        outputs=tco_local,
        summary="TCO baseline — local supplier",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )
    registry.record(
        tool_name="calc_tco",
        inputs={"path": "sea", "supplier": "SUP-SEA-03", "quantity": 1000},
        outputs=tco_sea,
        summary="TCO baseline — SEA supplier",
        invoked_at_round=rnd,
        invoked_by=invoked_by,
        source=source,
    )

    data_pack: dict[str, Any] = {
        "sku_focus": sku,
        "erp": erp_snapshot,
        "events": events,
        "market": market_payload.get("data", {}),
        "market_meta": {"fetched_at": market_payload.get("fetched_at")},
        "baseline_eoq": eoq_out,
        "baseline_mc": mc_out,
        "baseline_tco": {"local_supplier": tco_local, "sea_supplier": tco_sea},
        "suppliers_compare": [local, sea],
    }

    return {
        "tool_calls": tool_calls,
        "current_round_data_pack": data_pack,
    }
