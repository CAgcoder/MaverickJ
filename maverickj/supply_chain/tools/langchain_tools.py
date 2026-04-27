from __future__ import annotations

from langchain_core.tools import tool

from maverickj.schemas.supply_chain_engine import SupplyChainConfig
from maverickj.supply_chain.paths import resolve_supply_chain_paths
from maverickj.supply_chain.tools.eoq import calc_eoq
from maverickj.supply_chain.tools.erp import get_suppliers
from maverickj.supply_chain.tools.events import query_active_events
from maverickj.supply_chain.tools.market_data import fetch_cached
from maverickj.supply_chain.tools.monte_carlo import run_monte_carlo
from maverickj.supply_chain.tools.tco import calc_tco


@tool
def calc_eoq_tool(demand: float, setup_cost: float, holding_cost: float) -> dict:
    """Compute economic order quantity (EOQ) and related order metrics."""
    return calc_eoq(demand=demand, setup_cost=setup_cost, holding_cost=holding_cost)


@tool
def run_monte_carlo_tool(mean: float, std_dev: float, simulations: int = 1000) -> dict:
    """Simulate demand or lead-time uncertainty; returns distribution summaries."""
    return run_monte_carlo(mean=mean, std_dev=std_dev, simulations=simulations)


@tool
def calc_tco_tool(
    unit_price: float,
    freight: float,
    tariff: float,
    capital_cost: float,
    defect_rate: float,
    quantity: float = 1.0,
    rework_cost_per_defect: float = 0.0,
) -> dict:
    """Total cost of ownership for a procurement quantity with freight, tariff, and defects."""
    return calc_tco(
        unit_price=unit_price,
        freight=freight,
        tariff=tariff,
        capital_cost=capital_cost,
        defect_rate=defect_rate,
        quantity=quantity,
        rework_cost_per_defect=rework_cost_per_defect,
    )


def build_toolset(
    *,
    db_path: str | None = None,
    cache_path: str | None = None,
    events_path: str | None = None,
) -> list:
    """Return LangChain tools for Tier-2 agent turns.

    Paths default to ``SupplyChainConfig().data_path`` resolution so callers
    normally inject explicit paths from ``resolve_supply_chain_paths`` after warmup.
    """
    d, ev, cache = resolve_supply_chain_paths(SupplyChainConfig())
    db = db_path if db_path is not None else d
    events = events_path if events_path is not None else ev
    cache_file = cache_path if cache_path is not None else cache

    @tool
    def query_supplier_tool(region: str = "", max_price: float = -1, min_otif: float = -1) -> list[dict]:
        """Filter suppliers from the ERP SQLite database (db path fixed at bind time)."""
        return get_suppliers(
            db_path=db,
            region=region or None,
            max_price=None if max_price < 0 else max_price,
            min_otif=None if min_otif < 0 else min_otif,
        )

    @tool
    def query_events_tool(region: str = "", type: str = "", severity: str = "") -> list[dict]:
        """List active supply-chain disruption events (events file fixed at bind time)."""
        return query_active_events(
            region=region or None,
            type=type or None,
            severity=severity or None,
            events_path=events,
        )

    @tool
    def query_market_tool(ticker: str) -> dict:
        """Read a single ticker snapshot from the cached market JSON (cache path fixed at bind time)."""
        payload = fetch_cached(cache_file)
        return payload.get("data", {}).get(ticker, {"symbol": ticker, "price": None, "change_pct": None})

    return [
        calc_eoq_tool,
        run_monte_carlo_tool,
        calc_tco_tool,
        query_supplier_tool,
        query_events_tool,
        query_market_tool,
    ]

