"""Resolve supply-chain data file paths from config (single source of truth)."""

from __future__ import annotations

from pathlib import Path

from maverickj.schemas.supply_chain_engine import SupplyChainConfig


def resolve_supply_chain_paths(
    sc: SupplyChainConfig | None,
) -> tuple[str, str, str]:
    """Return ``(db_path, events_json_path, market_cache_json_path)`` as absolute strings."""
    cfg = sc or SupplyChainConfig()
    base = Path(cfg.data_path)
    if not base.is_absolute():
        base = Path.cwd() / base
    base = base.resolve()
    return (
        str(base / "seed.db"),
        str(base / "events.json"),
        str(base / "market_cache.json"),
    )
