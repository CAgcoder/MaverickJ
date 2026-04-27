from langchain_core.tools import tool

from maverickj.supply_chain.tools.eoq import calc_eoq
from maverickj.supply_chain.tools.erp import get_suppliers
from maverickj.supply_chain.tools.events import query_active_events
from maverickj.supply_chain.tools.market_data import fetch_cached
from maverickj.supply_chain.tools.monte_carlo import run_monte_carlo
from maverickj.supply_chain.tools.tco import calc_tco


@tool
def calc_eoq_tool(demand: float, setup_cost: float, holding_cost: float) -> dict:
    return calc_eoq(demand=demand, setup_cost=setup_cost, holding_cost=holding_cost)


@tool
def run_monte_carlo_tool(mean: float, std_dev: float, simulations: int = 1000) -> dict:
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
    return calc_tco(
        unit_price=unit_price,
        freight=freight,
        tariff=tariff,
        capital_cost=capital_cost,
        defect_rate=defect_rate,
        quantity=quantity,
        rework_cost_per_defect=rework_cost_per_defect,
    )


@tool
def query_supplier_tool(db_path: str, region: str = "", max_price: float = -1, min_otif: float = -1) -> list[dict]:
    return get_suppliers(
        db_path=db_path,
        region=region or None,
        max_price=None if max_price < 0 else max_price,
        min_otif=None if min_otif < 0 else min_otif,
    )


@tool
def query_events_tool(region: str = "", type: str = "", severity: str = "", events_path: str = "") -> list[dict]:
    return query_active_events(
        region=region or None,
        type=type or None,
        severity=severity or None,
        events_path=events_path or None,
    )


@tool
def query_market_tool(cache_path: str, ticker: str) -> dict:
    payload = fetch_cached(cache_path)
    return payload.get("data", {}).get(ticker, {"symbol": ticker, "price": None, "change_pct": None})


def build_toolset() -> list:
    return [
        calc_eoq_tool,
        run_monte_carlo_tool,
        calc_tco_tool,
        query_supplier_tool,
        query_events_tool,
        query_market_tool,
    ]

