"""Supply-chain mode: moderator with feasibility + relevance per argument id."""

from __future__ import annotations

from maverickj.schemas.debate import DebateState


def build_sc_moderator_user_appendix(state: DebateState) -> str:
    """Neutral ledger digest — moderator user message otherwise omits tool_calls entirely."""
    tc = state.tool_calls or {}
    by_src: dict[str, int] = {}
    for _k, rec in tc.items():
        if isinstance(rec, dict):
            src = str(rec.get("source") or "?")
            by_src[src] = by_src.get(src, 0) + 1
    lines = "\n".join(f"- `{k}`: {v}" for k, v in sorted(by_src.items()))
    if not lines.strip():
        lines = "- (none)"

    return f"""
## Supply-chain calibration (not a verdict)
- **Ledger**: {len(tc)} tool-call records total (warmup + Tier-2).
- **By `source`:**
{lines}
- Seed **events/market** intentionally include **stress scenarios** (e.g. active regional disruptions touching SEA lanes). That makes tail-risk arguments easy to articulate — it does **not** imply Risk wins by default. Judge **each argument id** on citations vs ledger + fact-check; do **not** systematically favour critic over advocate."""


def _collect_arg_ids(state: DebateState) -> list[str]:
    ids: list[str] = []
    if state.current_round_advocate:
        ids.extend(a.id for a in state.current_round_advocate.arguments)
    if state.current_round_critic:
        ids.extend(a.id for a in state.current_round_critic.arguments)
    return sorted(set(ids))


def build_sc_moderator_system_prompt(state: DebateState) -> str:
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"
    ids = _collect_arg_ids(state)
    id_list = ", ".join(f"`{i}`" for i in ids) if ids else "(none this round)"
    return f"""You are the **Supply-Chain Debate Moderator** — neutral, process-focused, and **implementation-aware**.

## Your role
- Summarize the round, judge whether the debate is converging, and set `should_continue`.
- In supply-chain mode you must also score each **active argument** from both sides on **feasibility** and **relevance** to the decision question.
- Output in **{lang}**.

## Tasks
1. `round_summary` — concise synthesis: where Cost and Risk still disagree, and any shared ground.
2. `key_divergences` — 3–6 short strings on unresolved cruxes (e.g. TCO vs service level, single-source vs dual-source).
3. `convergence_score` in [0,1] (same heuristics as the generic moderator: fewer novel claims + more concessions + narrower divergences → higher).
4. `should_continue` / `guidance_for_next_round` per convergence rules below.
5. **Per-argument scores** (required):
   - `feasibility_scores`: map **argument_id → float 0–10** (can this be executed in practice given lead times, MOQ, data gaps, and supplier mix?).
   - `relevance_scores`: map **argument_id → float 0–10** (does this point directly help decide the stated question, or is it off-topic?).
   - You **must** include an entry for every argument id listed: {id_list}
   - If a side only uses strategic framing without data, you may still score but explain tension in `round_summary`.

## Convergence rules
- `convergence_score` ≥ {state.config.convergence_score_target} and no substantive new arguments for {state.config.convergence_threshold} consecutive rounds → `should_continue` = false.
- Round {state.current_round} / max {state.config.max_rounds}; if current round = max → `should_continue` = false.

## Output format
- `key_divergences` must be a **JSON array** of strings, not a serialized string.
- `feasibility_scores` and `relevance_scores` must be **JSON objects** (string keys → float values), e.g. `{{"COST-R1-01": 7.5, "RISK-R1-01": 8.0}}`.
- **NEVER** serialize any array or object as a single quoted string.
- Return raw JSON only for structured fields.
- Vivid downside scenarios in the transcript are **stress inputs**, not automatic wins for Risk — weigh Cost-side ledger-backed economics vs Risk-side resilience **fairly per argument id**."""
