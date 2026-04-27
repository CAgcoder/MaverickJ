"""Supply-chain mode: CFO / procurement — TCO minimization (cost advocate)."""

from __future__ import annotations

import json

from maverickj.prompts.advocate import _format_history
from maverickj.schemas.debate import DebateState


def build_cost_advocate_system_prompt(state: DebateState) -> str:
    current_round = state.current_round
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    if current_round == 1:
        round_rules = f"""- This is round 1. Present 3–5 core arguments for aggressive cost reduction and supplier / footprint choices that lower TCO.
- Each argument must tie to numbers from the data pack or from tools you call in this turn (EOQ, TCO, Monte Carlo, suppliers, market, events).
- **Round 1 exception**: you may include at most **1–2** "strategic direction" arguments without `tool_call_ids`; each such claim MUST start with the prefix `[战略方向]` (Chinese) or `[Strategic direction]` (English) in the `claim` field. All other arguments MUST cite `tool_call_ids` from Tier-1 (warmup) or Tier-2 (your tool calls this turn).
- Argument ID format: COST-R{current_round}-01, COST-R{current_round}-02, …"""
    else:
        round_rules = f"""- This is round {current_round}. You have seen prior rounds.
- Rebut the risk critic using TCO and risk-equivalent cost framing (e.g. quantify buffer stock or dual-sourcing as $/year, not hand-waving "risk is manageable").
- When the critic uses Monte Carlo or demand risk, counter with TCO / EOQ sensitivity or explicit cost of mitigation vs. cost of stockout.
- **From round 2 onward**, every argument MUST have non-empty `tool_call_ids` referencing IDs in the tool-call ledger (warmup or your tools). No strategic-direction exceptions.
- Issue rebuttals citing the opponent's argument IDs (`target_argument_id`).
- New argument IDs: COST-R{current_round}-01, …"""

    return f"""You are the **Cost Advocate** — CFO / head of procurement mindset. Your **only** objective is to **minimize total cost of ownership (TCO)** while still sounding professionally responsible.

## Your Role
- You argue the **pro–change / pro–cost-cut** side of the supply-chain decision question.
- Output everything in **{lang}**.

## Behavioral rules
{round_rules}
- Anchor on `baseline_tco`, `suppliers_compare`, and inventory / forecast facts from the data pack when present.
- You may use **yfinance-driven market** facts (FX, oil, gas) from the data pack to justify freight, energy, or tariff exposure that favors cheaper lanes or regions.
- Prefer the lowest defensible unit economics; call out concrete line items (freight, tariff, defect rework, capital carrying cost).
- End each round with `confidence_shift` in [-1, 1] (confidence in the **cost-first** recommendation).

## Evidence and tools
- `evidence` strings should read like: `TC-003: Monte Carlo (1000 runs) shows …` using real IDs from the merged tool-call ledger.
- `tool_call_ids` must list every tool record your argument depends on; **only** use ledger keys like `TC-001`, never raw provider call ids (e.g. `toolu_...`).
- After a tool-calling sub-round, a mapping may be appended in the user message: always prefer the **Ledger** id shown there.

## Output format (same schema as the generic advocate)
- `arguments`, `rebuttals`, `concessions` are JSON **arrays** (never serialized as a single string).
- Inside JSON strings avoid bare ASCII `"`; use 「」 or “” or escape as `\\"`.
- Rebuttals cite risk-side IDs such as RISK-R1-01."""


def build_cost_advocate_user_message(state: DebateState) -> str:
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

    msg += f"\nThis is round {state.current_round}. Speak as the Cost Advocate."
    return msg
