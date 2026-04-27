"""Supply-chain mode: COO / supply-chain director — resilience (risk critic)."""

from __future__ import annotations

import json

from maverickj.prompts.advocate import _format_history
from maverickj.prompts.critic import _format_advocate_output
from maverickj.schemas.debate import DebateState


def build_risk_critic_system_prompt(state: DebateState) -> str:
    current_round = state.current_round
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    return f"""You are the **Risk Critic** — COO / supply-chain director mindset. Your **only** objective is **supply-chain resilience** (service level, continuity, tail risk), not lowest sticker price.

## Your Role
- You systematically challenge the Cost Advocate and build the **risk-first / con–reckless–cost–cutting** case.
- Output everything in **{lang}**.

## The three risk pillars (cover each across your arguments every round when relevant)
1. **Operational risk** — Use `baseline_mc` and Monte Carlo thinking: stockout / backlog probabilities, demand volatility. Challenge suppliers using `otif_rate`, `lead_time_days`, MOQ, and single-source exposure.
2. **Market risk** — Use `market` / FX / commodities from the data pack; you may call `query_market_tool` to stress-test trends. Tie macro moves to landed cost volatility and contract exposure.
3. **Geopolitical / disruption risk** — Use `events` from the data pack; call `query_events_tool` with the candidate region and severity filters to surface strikes, sanctions, port disruption, tariff shocks. For each high-severity event, give a concise **probability × impact** narrative (e.g. days of supply at risk, switching cost).

## Rebuttal discipline
- When the advocate leans on TCO or EOQ savings, counter with **probability-weighted loss** (stockout cost, expedite, revenue at risk) using Monte Carlo or scenario reasoning grounded in tool outputs and data-pack baselines.
- For cross-border / ocean freight paths, stack **market + geopolitical** tail risks explicitly.
- Avoid **single_point_failure** (always discuss backup / dual source). Avoid **lead_time_optimism** — use OTIF and statistical lead-time uncertainty, not best-case transits.

## IDs and format
- Your argument IDs: RISK-R{current_round}-01, RISK-R{current_round}-02, …
- Rebuttals must cite Cost Advocate IDs (e.g. COST-R1-01).
- `evidence` must reference tool call IDs like `TC-00x: …` when claiming quantitative facts; **only** ledger keys `TC-***` — never raw provider ids (`toolu_...`).
- `tool_call_ids` must be non-empty whenever you cite numeric/tool-backed claims (same ledger as warmup + your Tier-2 calls).
- `arguments`, `rebuttals`, `concessions` are JSON **arrays** only; report `confidence_shift` in [-1, 1] for confidence in the **resilience-first** position."""


def build_risk_critic_user_message(state: DebateState) -> str:
    msg = f"## Decision Question\n{state.question}\n"
    if state.context:
        msg += f"\n## Additional Context\n{state.context}\n"

    pack = state.current_round_data_pack
    if pack:
        msg += "\n## Current round data pack (Tier-1 baseline)\n"
        msg += "```json\n"
        msg += json.dumps(pack, ensure_ascii=False, default=str)[:24000]
        msg += "\n```\n"

    if state.tool_calls:
        msg += "\n## Tool call ledger (IDs you may cite)\n"
        msg += "```json\n"
        msg += json.dumps(state.tool_calls, ensure_ascii=False, default=str)[:12000]
        msg += "\n```\n"

    msg += f"\n## Debate History\n{_format_history(state.rounds)}\n"

    if state.rounds:
        guidance = state.rounds[-1].moderator.guidance_for_next_round
        if guidance:
            msg += f"\n## Moderator Guidance\n{guidance}\n"

    if state.current_round_advocate:
        msg += f"\n\n{_format_advocate_output(state.current_round_advocate)}"

    msg += f"\n\nThis is round {state.current_round}. Speak as the Risk Critic: rebut the Cost Advocate and present your resilience case."
    return msg
