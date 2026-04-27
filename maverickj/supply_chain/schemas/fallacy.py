"""Supply-chain–specific fallacy types (Enum for prompts and optional validation)."""

from __future__ import annotations

from enum import Enum


class SupplyChainFallacy(str, Enum):
    """White-list values for `FactCheck.fallacy_type` in supply_chain mode (field remains `str` elsewhere)."""

    local_optima_trap = "local_optima_trap"
    bullwhip_blindspot = "bullwhip_blindspot"
    sunk_cost_fallacy = "sunk_cost_fallacy"
    single_point_failure = "single_point_failure"
    safety_stock_denial = "safety_stock_denial"
    lead_time_optimism = "lead_time_optimism"
