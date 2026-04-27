from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yfinance as yf


def _is_cache_valid(cache_payload: dict[str, Any], cache_ttl_hours: int) -> bool:
    fetched_at = cache_payload.get("fetched_at")
    if not fetched_at:
        return False
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return datetime.now(timezone.utc) - ts <= timedelta(hours=cache_ttl_hours)


def fetch_cached(cache_path: str) -> dict[str, Any]:
    path = Path(cache_path)
    if not path.exists():
        return {"fetched_at": None, "data": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_and_cache(
    tickers: list[str],
    cache_path: str,
    cache_ttl_hours: int = 6,
    offline_mode: bool = False,
) -> dict[str, Any]:
    cached = fetch_cached(cache_path)
    if cached.get("data") and _is_cache_valid(cached, cache_ttl_hours):
        return cached
    if offline_mode and cached.get("data"):
        return cached
    if offline_mode:
        return {"fetched_at": None, "data": {}}

    data: dict[str, Any] = {}
    for symbol in tickers:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = float(info.get("last_price") or 0.0)
        prev = float(info.get("previous_close") or price or 1.0)
        change_pct = 0.0 if prev == 0 else (price - prev) / prev
        data[symbol] = {
            "symbol": symbol,
            "price": round(price, 4),
            "change_pct": round(change_pct, 6),
        }

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": data,
    }
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

