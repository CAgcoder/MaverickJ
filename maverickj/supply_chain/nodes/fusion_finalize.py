"""Tier 3 — merge critiques into FusedDecision."""

from __future__ import annotations

import logging
from typing import Any

from maverickj.agents.base import BaseAgent
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.prompts.fusion_synthesizer import (
    build_fusion_finalize_system_prompt,
    build_fusion_finalize_user_message,
)
from maverickj.supply_chain.schemas.fusion import ConvergenceCritique, FusedDecision, FusionDraft

logger = logging.getLogger(__name__)


def _coerce_draft(d: Any) -> FusionDraft:
    if isinstance(d, FusionDraft):
        return d
    if isinstance(d, dict):
        return FusionDraft(**d)
    raise TypeError(f"expected FusionDraft, got {type(d)}")


def _coerce_critiques(raw: Any) -> list[ConvergenceCritique]:
    if not raw:
        return []
    out: list[ConvergenceCritique] = []
    for item in raw:
        if isinstance(item, ConvergenceCritique):
            out.append(item)
        elif isinstance(item, dict):
            out.append(ConvergenceCritique(**item))
    return out


def _bump_metadata(state: DebateState, usage: dict) -> Any:
    inp = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    out = usage.get("output_tokens", usage.get("completion_tokens", 0))
    return state.metadata.model_copy(
        update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + inp + out,
        }
    )


async def fusion_finalize_node(state: DebateState, router: ModelRouter) -> dict[str, Any]:
    """Single LLM merge of draft + critiques → final_fused_decision."""
    logger.info("=== Fusion finalize ===")
    if state.fusion_draft is None:
        return {}

    draft = _coerce_draft(state.fusion_draft)
    critiques = _coerce_critiques(state.convergence_critiques)

    agent = BaseAgent(router)
    agent.role = "fusion_synthesizer"
    system_prompt = build_fusion_finalize_system_prompt(state)
    user_message = build_fusion_finalize_user_message(state, draft=draft, critiques=critiques)
    fused, usage = await agent.invoke(system_prompt, user_message, FusedDecision)

    return {
        "final_fused_decision": fused,
        "metadata": _bump_metadata(state, usage),
    }
