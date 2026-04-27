"""Tier 3 — parallel cost + risk convergence critiques on the fusion draft."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from maverickj.agents.base import BaseAgent
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.prompts.convergence_critic import (
    build_convergence_critique_user_message,
    build_cost_convergence_system_prompt,
    build_risk_convergence_system_prompt,
)
from maverickj.supply_chain.schemas.fusion import ConvergenceCritique, ConvergenceCritiqueOutput, FusionDraft

logger = logging.getLogger(__name__)


def _coerce_draft(d: Any) -> FusionDraft:
    if isinstance(d, FusionDraft):
        return d
    if isinstance(d, dict):
        return FusionDraft(**d)
    raise TypeError(f"expected FusionDraft, got {type(d)}")


def _merge_usage(u1: dict, u2: dict) -> dict:
    def _tok(u: dict, key_in: str, key_alt: str) -> int:
        return int(u.get(key_in, u.get(key_alt, 0)))

    return {
        "input_tokens": _tok(u1, "input_tokens", "prompt_tokens") + _tok(u2, "input_tokens", "prompt_tokens"),
        "output_tokens": _tok(u1, "output_tokens", "completion_tokens") + _tok(u2, "output_tokens", "completion_tokens"),
    }


def _bump_metadata(state: DebateState, usage: dict) -> Any:
    inp = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    out = usage.get("output_tokens", usage.get("completion_tokens", 0))
    return state.metadata.model_copy(
        update={
            "total_llm_calls": state.metadata.total_llm_calls + 2,
            "total_tokens_used": state.metadata.total_tokens_used + inp + out,
        }
    )


async def convergence_critique_node(state: DebateState, router: ModelRouter) -> dict[str, Any]:
    """Serial LLM calls for cost + risk perspectives (structured critiques only)."""
    logger.info("=== Convergence critique (cost + risk) ===")
    if state.fusion_draft is None:
        return {"convergence_critiques": []}

    draft = _coerce_draft(state.fusion_draft)
    user_message = build_convergence_critique_user_message(state, draft)

    async def _run_cost() -> tuple[ConvergenceCritiqueOutput, dict]:
        agent = BaseAgent(router)
        agent.role = "convergence_critic"
        sp = build_cost_convergence_system_prompt(state)
        out, usage = await agent.invoke(sp, user_message, ConvergenceCritiqueOutput)
        return out, usage

    async def _run_risk() -> tuple[ConvergenceCritiqueOutput, dict]:
        agent = BaseAgent(router)
        agent.role = "convergence_critic"
        sp = build_risk_convergence_system_prompt(state)
        out, usage = await agent.invoke(sp, user_message, ConvergenceCritiqueOutput)
        return out, usage

    (cost_out, u1), (risk_out, u2) = await asyncio.gather(_run_cost(), _run_risk())
    merged_usage = _merge_usage(u1, u2)

    critiques: list[ConvergenceCritique] = [
        ConvergenceCritique(
            perspective="cost_advocate",
            critique_points=list(cost_out.critique_points or [])[:3],
            final_endorsement=bool(cost_out.final_endorsement),
        ),
        ConvergenceCritique(
            perspective="risk_critic",
            critique_points=list(risk_out.critique_points or [])[:3],
            final_endorsement=bool(risk_out.final_endorsement),
        ),
    ]

    return {
        "convergence_critiques": critiques,
        "metadata": _bump_metadata(state, merged_usage),
    }
