from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yfinance as yf


def _row_volume(row: Any) -> int | None:
    idx = getattr(row, "index", None)
    if idx is None or "Volume" not in idx:
        return None
    try:
        v = float(row["Volume"])
    except (TypeError, ValueError):
        return None
    if v != v or v < 0:  # NaN
        return None
    return int(v)


def _quote_one_symbol(symbol: str) -> dict[str, Any]:
    """Quote one symbol: price + change vs prior close, plus OHLCV when history exists.

    Futures (CL=F, NG=F) often lack usable fast_info; history(5d) fills OHLC and prior close.
    """
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    currency = info.get("currency") or info.get("quote_currency")

    price = float(info.get("last_price") or 0.0)
    prev = float(info.get("previous_close") or 0.0)

    hist = ticker.history(period="5d", auto_adjust=False)
    ohlcv: dict[str, Any] = {}
    as_of: str | None = None

    if hist is not None and not hist.empty and "Close" in hist.columns:
        last = hist.iloc[-1]
        prior = hist.iloc[-2] if len(hist) >= 2 else last
        close = float(last["Close"])
        if price <= 0:
            price = close
        if prev <= 0:
            prev = float(prior["Close"])

        o = float(last["Open"]) if "Open" in last else close
        h = float(last["High"]) if "High" in last else close
        l_ = float(last["Low"]) if "Low" in last else close
        vol = _row_volume(last)
        idx = hist.index[-1]
        as_of = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)

        ohlcv = {
            "open": round(o, 6),
            "high": round(h, 6),
            "low": round(l_, 6),
            "close": round(close, 6),
            "volume": vol,
            "as_of": as_of,
        }

    if prev <= 0:
        prev = price if price > 0 else 1.0
    change_pct = 0.0 if prev == 0 else (price - prev) / prev

    out: dict[str, Any] = {
        "symbol": symbol,
        "price": round(price, 6),
        "change_pct": round(change_pct, 6),
    }
    if currency:
        out["currency"] = str(currency)
    out.update(ohlcv)
    return out


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
        try:
            data[symbol] = _quote_one_symbol(symbol)
        except Exception as exc:  # noqa: BLE001
            data[symbol] = {
                "symbol": symbol,
                "price": None,
                "change_pct": None,
                "error": str(exc),
            }

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": data,
    }
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

