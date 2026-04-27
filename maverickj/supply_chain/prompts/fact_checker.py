"""Supply-chain mode: fact-checker with tool-citation rules + supply fallacies + scores."""

from __future__ import annotations

import json

from maverickj.schemas.agents import AgentResponse
from maverickj.schemas.debate import DebateState
from maverickj.supply_chain.schemas.fallacy import SupplyChainFallacy


def _format_sc_arguments(adv: AgentResponse | None, crt: AgentResponse | None) -> str:
    parts: list[str] = []
    if adv:
        parts.append("[Cost Advocate / Advocate arguments]\n")
        for a in adv.arguments:
            tids = ", ".join(a.tool_call_ids) if a.tool_call_ids else "(none)"
            parts.append(
                f"- [{a.id}] {a.claim}\n"
                f"  Reasoning: {a.reasoning}\n"
                f"  Evidence: {a.evidence or 'none'}\n"
                f"  tool_call_ids: {tids}\n"
                f"  Status: {a.status.value}"
            )
        parts.append(
            f"\nRebuttals: {'; '.join(f'Against {r.target_argument_id}: {r.counter_claim}' for r in adv.rebuttals) or 'none'}\n"
        )
    if crt:
        parts.append("\n[Risk Critic / Critic arguments]\n")
        for a in crt.arguments:
            tids = ", ".join(a.tool_call_ids) if a.tool_call_ids else "(none)"
            parts.append(
                f"- [{a.id}] {a.claim}\n"
                f"  Reasoning: {a.reasoning}\n"
                f"  Evidence: {a.evidence or 'none'}\n"
                f"  tool_call_ids: {tids}\n"
                f"  Status: {a.status.value}"
            )
        parts.append(
            f"\nRebuttals: {'; '.join(f'Against {r.target_argument_id}: {r.counter_claim}' for r in crt.rebuttals) or 'none'}\n"
        )
    return "\n".join(parts)


def _fallacy_block(lang: str) -> str:
    if lang == "Chinese":
        return "\n".join(
            [
                f"- `{e.value}`：{ _fallacy_zh(e) }" for e in SupplyChainFallacy
            ]
        )
    return "\n".join(
        [
            f"- `{e.value}`: { _fallacy_en(e) }" for e in SupplyChainFallacy
        ]
    )


def _fallacy_zh(e: SupplyChainFallacy) -> str:
    m = {
        SupplyChainFallacy.local_optima_trap: "局部最优：例如只省运费但忽略仓储/缺货成本。",
        SupplyChainFallacy.bullwhip_blindspot: "牛鞭效应盲区：忽略需求放大与订单波动。",
        SupplyChainFallacy.sunk_cost_fallacy: "沉没成本：因已投入而拒绝更换劣质来源。",
        SupplyChainFallacy.single_point_failure: "单点故障：只押一家供应商、无备份。",
        SupplyChainFallacy.safety_stock_denial: "否认安全库存必要。",
        SupplyChainFallacy.lead_time_optimism: "交期乐观：用最佳 case 的 lead time 做计划。",
    }
    return m[e]


def _fallacy_en(e: SupplyChainFallacy) -> str:
    m = {
        SupplyChainFallacy.local_optima_trap: "Local optima (e.g. save freight, ignore stockout/holding).",
        SupplyChainFallacy.bullwhip_blindspot: "Bullwhip blind spot.",
        SupplyChainFallacy.sunk_cost_fallacy: "Sunk cost (cling to a bad source).",
        SupplyChainFallacy.single_point_failure: "Single point of failure (no backup).",
        SupplyChainFallacy.safety_stock_denial: "Deny need for safety stock.",
        SupplyChainFallacy.lead_time_optimism: "Unrealistically optimistic lead times.",
    }
    return m[e]


def build_sc_fact_checker_system_prompt(state: DebateState) -> str:
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"
    rnd = state.current_round
    return f"""You are the **Supply-Chain Fact-Checker** — a neutral logic and evidence auditor for a procurement / resilience debate (Cost side vs Risk side).

## Your role
- You do not pick a winner; you judge **factual anchoring** and **logical soundness** of each active argument and rebuttal.
- Output in **{lang}**.

## Supply-chain fallacy catalog (set `fallacy_type` to one of these when applicable)
{_fallacy_block(lang)}

You may also use **generic** fallacy labels as strings when appropriate, e.g. `straw_man`, `slippery_slope`, `confirmation_bias`, `hasty_generalization`, `false_dilemma`, `appeal_to_authority`, or `fabricated_evidence` when evidence does not match the tool ledger.

## Tool ID and citation rules (strict)
- The ground-truth tool ledger is `state.tool_calls` (exposed in the user message as JSON). Keys look like `TC-001`, `TC-002`, …
- Every `tool_call_id` string cited in an argument’s **evidence** or listed in **tool_call_ids** **must** exist in that ledger. If a cited ID is missing, treat as **fabricated or mistaken reference** → prefer `verdict=flawed`, set `fallacy_type` to `fabricated_evidence` (or describe in explanation), and **low `factuality_score`**.
- If the argument’s numeric claim **contradicts** the `outputs` of the referenced `ToolCallRecord`, deduct **factuality_score** accordingly.
- **Round 1 only — Cost side exception**: the advocate may have at most 1–2 **strategic** arguments with **no** `tool_call_ids` if the `claim` is explicitly prefixed with `[战略方向]` or `[Strategic direction]`. Do **not** treat those as flawed solely for missing IDs. **From round 2 onward**, any non–strategic argument with **empty** `tool_call_ids` should receive `verdict=flawed` and `factuality_score=0` (unless you judge it as pure non-factual philosophy — still flag as `needs_context` or `flawed` per your rubric).
- The Risk side (RISK-… / critic) is **not** covered by the round-1 strategic exception; still apply tool rules whenever they make quantitative or data-backed claims.

## Scoring (per check, 0–10)
- `factuality_score`: alignment with **tool outputs** and internal consistency of numbers; **heavily** penalize missing/invalid `TC-***` references.
- `logic_score`: absence of the fallacies above; supply-chain structural mistakes (e.g. ignoring lead time vs safety stock) hit **logic_score**.

## Verdicts
Use the same `verdict` values as the generic engine: `valid`, `flawed`, `needs_context`, `unverifiable`.

## Output format
- `checks` is a **JSON array** of objects, one row per argument you evaluate (typically each **active** argument id from both sides this round). Each object must include at minimum:
  - `target_argument_id`, `verdict`, `explanation`
  - `fallacy_type` (string or null)
  - `correction` (optional)
  - `factuality_score` (float 0–10)
  - `logic_score` (float 0–10)
- **NEVER** serialize arrays as a single quoted string. No bare unescaped `"` inside JSON string values; use Chinese quotes or escape.
- `overall_assessment` summarizes the round’s evidentiary quality and the biggest supply-chain risk if claims are shaky.
- This is **round {rnd}**."""


def build_sc_fact_checker_user_message(state: DebateState) -> str:
    msg = f"## Decision Question\n{state.question}\n"
    if state.context:
        msg += f"\n## Additional Context\n{state.context}\n"
    if state.tool_calls:
        msg += "\n## Tool call ledger (authoritative; keys are TC-***)\n"
        msg += "```json\n"
        msg += json.dumps(state.tool_calls, ensure_ascii=False, default=str)[:14000]
        msg += "\n```\n"
    msg += "\n## Arguments and rebuttals to evaluate (this round)\n"
    msg += _format_sc_arguments(state.current_round_advocate, state.current_round_critic)
    msg += "\n\nFact-check and logic-check the above. Apply supply-chain fallacy and tool-ledger rules from the system prompt."
    return msg
