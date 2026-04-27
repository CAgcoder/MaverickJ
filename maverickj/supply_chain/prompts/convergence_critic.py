"""Constructive critique prompts (cost vs risk) on the fusion draft — no new primary arguments."""

from __future__ import annotations

import json

from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.schemas.fusion import FusionDraft


def _lang(state: DebateState) -> str:
    return "Chinese" if state.config.language in ("zh", "auto") else "English"


def build_cost_convergence_system_prompt(state: DebateState) -> str:
    lang = _lang(state)
    return f"""You are the **Cost Advocate** reviewing a **FusionDraft** (not starting a new debate round).
Output in **{lang}**.

Rules:
- Do **not** create new primary arguments or new IDs.
- Offer **1–3 constructive critique points** on the draft: TCO realism, missing cost levers, implementation friction, or sequencing for savings.
- Set `final_endorsement` to true only if the draft is acceptable as a cost-first basis (minor tweaks ok).
- Output schema: `critique_points` (list of strings), `final_endorsement` (bool)."""


def build_risk_convergence_system_prompt(state: DebateState) -> str:
    lang = _lang(state)
    return f"""You are the **Risk Critic** reviewing a **FusionDraft** (not starting a new debate round).
Output in **{lang}**.

Rules:
- Do **not** create new primary arguments or new IDs.
- Offer **1–3 constructive critique points**: demand/supply volatility, OTIF/lead-time, geopolitical or market tail risks, or mitigation gaps.
- Set `final_endorsement` to true only if resilience concerns are adequately reflected (minor gaps ok).
- Output schema: `critique_points` (list of strings), `final_endorsement` (bool)."""


def build_convergence_critique_user_message(state: DebateState, draft: FusionDraft) -> str:
    payload = {
        "question": state.question,
        "context": state.context,
        "fusion_draft": draft.model_dump(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
