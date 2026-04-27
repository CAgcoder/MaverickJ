from __future__ import annotations


def calc_tco(
    *,
    unit_price: float,
    freight: float,
    tariff: float,
    capital_cost: float,
    defect_rate: float,
    quantity: float = 1.0,
    rework_cost_per_defect: float = 0.0,
) -> dict:
    """Total cost of ownership breakdown."""
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if defect_rate < 0 or defect_rate > 1:
        raise ValueError("defect_rate must be in [0,1]")

    purchase_cost = unit_price * quantity
    freight_cost = freight * quantity
    tariff_cost = tariff * quantity
    working_capital_cost = capital_cost * quantity
    expected_defect_cost = quantity * defect_rate * rework_cost_per_defect
    total = purchase_cost + freight_cost + tariff_cost + working_capital_cost + expected_defect_cost
    return {
        "quantity": quantity,
        "purchase_cost": round(purchase_cost, 2),
        "freight_cost": round(freight_cost, 2),
        "tariff_cost": round(tariff_cost, 2),
        "working_capital_cost": round(working_capital_cost, 2),
        "expected_defect_cost": round(expected_defect_cost, 2),
        "total_tco": round(total, 2),
    }

