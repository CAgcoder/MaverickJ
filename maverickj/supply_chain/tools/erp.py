from __future__ import annotations

import sqlite3
from typing import Any

from maverickj.supply_chain.data.data_loader import init_db


def _query_all(db_path: str, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_inventory(db_path: str, sku: str | None = None) -> list[dict[str, Any]]:
    if sku:
        return _query_all(db_path, "SELECT * FROM Inventory WHERE sku = ?", (sku,))
    return _query_all(db_path, "SELECT * FROM Inventory")


def get_suppliers(
    db_path: str,
    region: str | None = None,
    max_price: float | None = None,
    min_otif: float | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM Supplier WHERE 1=1"
    params: list[Any] = []
    if region:
        sql += " AND region = ?"
        params.append(region)
    if max_price is not None:
        sql += " AND unit_price <= ?"
        params.append(max_price)
    if min_otif is not None:
        sql += " AND otif_rate >= ?"
        params.append(min_otif)
    return _query_all(db_path, sql, tuple(params))


def get_forecast(db_path: str, sku: str) -> list[dict[str, Any]]:
    return _query_all(
        db_path,
        "SELECT * FROM Sales_Forecast WHERE sku = ? ORDER BY week_ahead ASC",
        (sku,),
    )


def get_full_snapshot(db_path: str) -> dict[str, Any]:
    return {
        "inventory": get_inventory(db_path),
        "suppliers": get_suppliers(db_path),
        "forecast": _query_all(db_path, "SELECT * FROM Sales_Forecast ORDER BY sku, week_ahead"),
    }

