"""Supply-chain mode: decision matrix + data evidence + minority + circuit breakers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.schemas.fusion import ConvergenceCritique, FusedDecision, FusionDraft


def _dump_tool_calls(state: DebateState, *, limit: int = 80) -> str:
    tc = state.tool_calls or {}
    items: list[dict[str, Any]] = []
    for _k, v in list(tc.items())[:limit]:
        if hasattr(v, "model_dump"):
            items.append(v.model_dump(mode="json"))
        elif isinstance(v, dict):
            items.append(v)
    return json.dumps(items, ensure_ascii=False, indent=2)


def build_sc_report_generator_system_prompt(state: DebateState) -> str:
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    return f"""You are a **supply-chain decision report generator**. Produce a structured `DecisionReport` in **{lang}**.

## Core sections (same as generic reports)
1. **executive_summary**: 3–5 sentences covering cost vs risk trade-offs and the fused consensus when present.
2. **recommendation**: direction, confidence (high/medium/low), preconditions — grounded in surviving arguments and `final_fused_decision` when available.
3. **pro_arguments / con_arguments**: Only advocate vs critic arguments with status active/modified; sort by strength (rules: base 5; +1 per survived rebuttal; +1 if latest fact-check valid; −3 if flawed).
4. **resolved_disagreements / unresolved_disagreements / risk_factors / next_steps**: concrete and specific.

## Supply-chain-only fields (required in this mode)
5. **decision_matrix**: **at least 2** `DecisionOption` rows:
   - Derive paths from `final_fused_decision.final_consensus` and `consensus_actions` when present (recommended path + 1–2 alternates).
   - Each row: `path_name`, `expected_tco_usd`, `implementation_cost_usd` (nullable if unknown), `risk_warnings` (strings), `supporting_tool_calls` (TC-* IDs from the ledger that support that row).

6. **data_evidence**: A **subset** of the tool-call ledger (your choice of the most decision-critical records). Represent each as objects with at least: id, tool_name, summary, and key numeric fields from outputs (EOQ / Monte Carlo / TCO / market / events as relevant). Do not fabricate IDs — only IDs present in the ledger appendix.

7. **minority_report**: List of strings — typically align with `final_fused_decision.remaining_disagreements`. If none, briefly note consensus or leave one honest residual risk line.

8. **circuit_breakers**: **At least 1** row. Each must include:
   - `trigger_metric`: prefer a real ticker key seen in tool/market data (**CL=F**, **NG=F**, or **EUR=X**).
   - `threshold_value`, `trigger_condition`, `fallback_action`, `rationale`.
   Ground triggers in volatility / geopolitical / cost scenarios implied by events + market data (do not invent prices not suggested by the transcript).

## Output rules
- Output **one JSON object** matching the DecisionReport schema. Omit `debate_stats` (filled by the engine).
- **Sections 5–8 are mandatory.** Do **not** omit them or use empty arrays `[]` unless explicitly justified for `minority_report` only; **decision_matrix**, **data_evidence**, and **circuit_breakers** must always be non-empty lists matching the minimum counts above.
- Never invent tool-call IDs; cite only from the provided ledger.
- Keep numeric claims consistent with ledger outputs where cited."""


def build_sc_report_generator_user_message(state: DebateState) -> str:
    from maverickj.prompts.report_generator import _build_generic_report_generator_user_message

    base = _build_generic_report_generator_user_message(state)

    def _fd(raw: Any, model: type[BaseModel]):
        if raw is None:
            return None
        if isinstance(raw, model):
            return raw
        if isinstance(raw, dict):
            try:
                return model.model_validate(raw)
            except Exception:
                return None
        return None

    fd = _fd(state.final_fused_decision, FusedDecision)
    fusion_draft = _fd(state.fusion_draft, FusionDraft)

    appendix = "\n\n## Supply-chain fusion outputs\n\n"
    appendix += "### fusion_draft\n"
    appendix += json.dumps(fusion_draft.model_dump() if fusion_draft else {}, ensure_ascii=False, indent=2)
    appendix += "\n\n### final_fused_decision\n"
    appendix += json.dumps(fd.model_dump() if fd else {}, ensure_ascii=False, indent=2)
    appendix += "\n\n### convergence_critiques\n"

    def _crit_dump(c: Any) -> dict:
        if isinstance(c, ConvergenceCritique):
            return c.model_dump()
        if hasattr(c, "model_dump"):
            return c.model_dump()
        return c if isinstance(c, dict) else {"value": str(c)}

    appendix += json.dumps([_crit_dump(c) for c in (state.convergence_critiques or [])], ensure_ascii=False, indent=2)
    appendix += "\n\n### tool_calls ledger (subset allowed in data_evidence)\n"
    appendix += _dump_tool_calls(state)
    appendix += "\n\nFill decision_matrix, data_evidence, minority_report, and circuit_breakers per system instructions."
    return base + appendix
