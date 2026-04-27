"""LLM prompts for fusion synthesis and fusion finalize (merge critiques)."""

from __future__ import annotations

import json

from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.fusion_scoring import ScoredArgumentForFusion
from maverickj.supply_chain.schemas.fusion import ConvergenceCritique, FusionDraft


def _lang(state: DebateState) -> str:
    return "Chinese" if state.config.language in ("zh", "auto") else "English"


def build_fusion_synthesis_system_prompt(state: DebateState) -> str:
    lang = _lang(state)
    return f"""You are the **Fusion Synthesizer** for a supply-chain debate.
Output in **{lang}**.

Task: receive **high-scoring arguments** (already filtered by score thresholds) plus the original question.
Produce a **FusionDraft**:
- `high_score_arguments`: echo the input list (same IDs and scores; you may reorder).
- `proposed_consensus`: one coherent narrative that merges the strongest evidence-backed themes. Do **not** invent new numerical claims; ground wording in the provided argument text.
- `consensus_actions`: 3–7 concrete, actionable steps (who/what/when style where possible).
- `open_questions`: residual uncertainties or data gaps (not new unsupported opinions).

Rules:
- Do not introduce new tool-call IDs or fake statistics.
- If the candidate list is empty, state clearly that no arguments met the bar and keep actions/questions minimal and honest."""


def build_fusion_synthesis_user_message(
    state: DebateState,
    *,
    candidates: list[ScoredArgumentForFusion],
) -> str:
    payload = {
        "question": state.question,
        "context": state.context,
        "candidates": [
            {
                "argument_id": c.argument_id,
                "raised_by": c.raised_by,
                "claim": c.claim,
                "factuality": round(c.factuality, 2),
                "logic": round(c.logic, 2),
                "feasibility": round(c.feasibility, 2),
                "relevance": round(c.relevance, 2),
                "composite": round(c.composite, 2),
            }
            for c in candidates
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_fusion_finalize_system_prompt(state: DebateState) -> str:
    lang = _lang(state)
    return f"""You are the **Fusion Finalizer** for a supply-chain debate.
Output in **{lang}**.

You receive:
1. The latest `FusionDraft` (consensus proposal).
2. Two critiques from **Cost Advocate** and **Risk Critic** perspectives (constructive only; they must not invent new primary arguments).

Produce a **FusedDecision**:
- `final_consensus`: integrate the draft + accepted critique insights into one decision narrative.
- `accepted_amendments`: bullet list of critique points you incorporated (paraphrase ok).
- `rejected_amendments_with_reason`: critique suggestions you did **not** take, each with a short reason.
- `remaining_disagreements`: genuine residual tensions between cost vs risk (for a minority report); be specific.

Rules:
- Never invent numbers or tool IDs not implied by the inputs.
- Keep `remaining_disagreements` honest — if both sides largely agree after critique, say so briefly."""


def build_fusion_finalize_user_message(
    state: DebateState,
    *,
    draft: FusionDraft,
    critiques: list[ConvergenceCritique],
) -> str:
    payload = {
        "question": state.question,
        "fusion_draft": draft.model_dump(),
        "convergence_critiques": [c.model_dump() for c in critiques],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
