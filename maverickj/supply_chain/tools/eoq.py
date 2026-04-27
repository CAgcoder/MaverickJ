import math


def calc_eoq(demand: float, setup_cost: float, holding_cost: float) -> dict:
    """Economic Order Quantity."""
    if demand <= 0 or setup_cost <= 0 or holding_cost <= 0:
        raise ValueError("demand/setup_cost/holding_cost must be > 0")

    eoq = math.sqrt((2 * demand * setup_cost) / holding_cost)
    annual_order_cost = (demand / eoq) * setup_cost
    annual_holding_cost = (eoq / 2) * holding_cost
    total_annual_cost = annual_order_cost + annual_holding_cost
    return {
        "eoq": round(eoq, 2),
        "annual_order_cost": round(annual_order_cost, 2),
        "annual_holding_cost": round(annual_holding_cost, 2),
        "total_annual_cost": round(total_annual_cost, 2),
    }

