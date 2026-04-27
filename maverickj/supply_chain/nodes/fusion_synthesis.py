"""Tier 3 — fusion synthesis: threshold-filter arguments → FusionDraft."""

from __future__ import annotations

import logging
from typing import Any

from maverickj.agents.base import BaseAgent
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState
from maverickj.schemas.supply_chain_engine import SupplyChainConfig
from maverickj.supply_chain.fusion_scoring import collect_scored_arguments, filter_high_score_arguments
from maverickj.supply_chain.prompts.fusion_synthesizer import (
    build_fusion_synthesis_system_prompt,
    build_fusion_synthesis_user_message,
)
from maverickj.supply_chain.schemas.fusion import FusionDraft, HighScoreArgumentEntry

logger = logging.getLogger(__name__)


def _bump_metadata(state: DebateState, usage: dict) -> Any:
    inp = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    out = usage.get("output_tokens", usage.get("completion_tokens", 0))
    return state.metadata.model_copy(
        update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + inp + out,
        }
    )


def _coerce_fusion_draft(d: Any) -> FusionDraft:
    if isinstance(d, FusionDraft):
        return d
    if isinstance(d, dict):
        return FusionDraft(**d)
    raise TypeError(f"expected FusionDraft, got {type(d)}")


async def fusion_synthesis_node(state: DebateState, router: ModelRouter) -> dict[str, Any]:
    """Select high-score arguments and call fusion_synthesizer to produce a draft."""
    logger.info("=== Fusion synthesis ===")
    sc = state.supply_chain_config or SupplyChainConfig()
    scored = collect_scored_arguments(state)
    candidates = filter_high_score_arguments(scored, sc)

    lang_zh = state.config.language in ("zh", "auto")
    if not candidates:
        msg = (
            f"当前没有论点同时满足综合分≥{sc.fusion.composite_score_threshold}且事实性≥{sc.fusion.factuality_score_threshold}。"
            if lang_zh
            else (
                f"No arguments met fusion thresholds (composite≥{sc.fusion.composite_score_threshold}, "
                f"factuality≥{sc.fusion.factuality_score_threshold})."
            )
        )
        return {
            "fusion_draft": FusionDraft(
                high_score_arguments=[],
                proposed_consensus=msg,
                consensus_actions=[],
                open_questions=[
                    "补充辩论回合或检查 moderator / fact_checker 评分是否写入。"
                    if lang_zh
                    else "Add rounds or ensure moderator and fact-check scores are populated.",
                ],
            ),
        }

    agent = BaseAgent(router)
    agent.role = "fusion_synthesizer"
    system_prompt = build_fusion_synthesis_system_prompt(state)
    user_message = build_fusion_synthesis_user_message(state, candidates=candidates)
    draft_raw, usage = await agent.invoke(system_prompt, user_message, FusionDraft)
    draft = _coerce_fusion_draft(draft_raw)

    echo = [
        HighScoreArgumentEntry(
            argument_id=c.argument_id,
            composite_score=round(c.composite, 2),
            factuality_score=round(c.factuality, 2),
        )
        for c in candidates
    ]
    draft = draft.model_copy(update={"high_score_arguments": echo})

    return {
        "fusion_draft": draft,
        "metadata": _bump_metadata(state, usage),
    }
