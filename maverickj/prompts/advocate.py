from maverickj.schemas.debate import DebateRound, DebateState


def _format_history(rounds: list[DebateRound]) -> str:
    if not rounds:
        return "(No debate history yet)"
    parts = []
    for r in rounds:
        adv = r.advocate
        crt = r.critic
        fc = r.fact_check
        mod = r.moderator
        parts.append(
            f"=== Round {r.round_number} ===\n"
            f"[Advocate's Arguments]\n"
            + "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in adv.arguments)
            + f"\nRebuttals: {'; '.join(f'Against {rb.target_argument_id}: {rb.counter_claim}' for rb in adv.rebuttals) or 'none'}"
            f"\nConcessions: {'; '.join(adv.concessions) or 'none'}"
            f"\nConfidence Shift: {adv.confidence_shift}"
            f"\n\n[Critic's Arguments]\n"
            + "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in crt.arguments)
            + f"\nRebuttals: {'; '.join(f'Against {rb.target_argument_id}: {rb.counter_claim}' for rb in crt.rebuttals) or 'none'}"
            f"\nConcessions: {'; '.join(crt.concessions) or 'none'}"
            f"\nConfidence Shift: {crt.confidence_shift}"
            f"\n\n[Fact Check]\n"
            + "\n".join(f"- {c.target_argument_id}: {c.verdict.value} - {c.explanation}" for c in fc.checks)
            + f"\nOverall Assessment: {fc.overall_assessment}"
            f"\n\n[Moderator Summary]\n{mod.round_summary}"
            f"\nKey Divergences: {'; '.join(mod.key_divergences)}"
            f"\nConvergence Score: {mod.convergence_score}"
        )
    return "\n\n".join(parts)


def build_advocate_system_prompt(state: DebateState) -> str:
    if state.config.mode == "supply_chain":
        from maverickj.supply_chain.prompts import cost_advocate

        return cost_advocate.build_cost_advocate_system_prompt(state)

    current_round = state.current_round
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    if current_round == 1:
        round_rules = f"""- This is round 1. Present 3-5 core pro-side arguments independently.
- Each argument must have a clear claim, reasoning process, and supporting evidence.
- Argument ID format: ADV-R{current_round}-01, ADV-R{current_round}-02, ..."""
    else:
        round_rules = f"""- This is round {current_round}. You have seen the previous debate history.
- You must respond to the Critic's rebuttals and the Fact-Checker's verdicts.
- For effectively rebutted arguments: revise your position or concede (add to concessions).
- For partially rebutted arguments: supplement reasoning, refine wording (set argument status to modified).
- You may introduce new arguments to strengthen the overall pro-side case.
- Issue your own rebuttals against the Critic's arguments; cite the opponent's argument ID (target_argument_id).
- New argument ID format: ADV-R{current_round}-01, ADV-R{current_round}-02, ..."""

    return f"""You are a senior business strategy consultant responsible for arguing the pro-side position (i.e., "should do") in the debate.

## Your Role
- You are the Advocate. Your goal is to build the strongest possible pro-side case for the decision question.
- You must output everything in {lang}.

## Behavioral Rules
{round_rules}
- At the end of each round, report confidence_shift: your change in confidence in the pro-side position (between -1 and 1; negative means decreased confidence).
- Do not ignore valid rebuttals from the opponent.
- Do not repeat arguments that have already been refuted.
- Only concede when the opponent's argument is genuinely unassailable.

## ⚠️ Output Format Requirements
- `arguments` MUST be a JSON **array** of objects, e.g. [{{"id": "ADV-R{current_round}-01", "claim": "...", "reasoning": "...", "status": "active"}}]
- `rebuttals` MUST be a JSON **array** of objects, e.g. [{{"target_argument_id": "CRT-R1-01", "counter_claim": "...", "reasoning": "..."}}]
- `concessions` MUST be a JSON **array** of strings, e.g. ["point A", "point B"]
- Inside any JSON string value, **NEVER** write bare `"` characters as normal prose punctuation.
- If you need quotation marks in Chinese text, use `「」` or `“”`; if you must use ASCII quotes, escape them as `\\"`.
- Every field value must remain valid JSON after serialization. Invalid example: `"将"竞争激烈"等同于"不可行""`; valid example: `"将「竞争激烈」等同于「不可行」"`.
- **NEVER** serialize any array as a quoted string. Return raw JSON arrays only."""


def build_advocate_user_message(state: DebateState) -> str:
    if state.config.mode == "supply_chain":
        from maverickj.supply_chain.prompts import cost_advocate

        return cost_advocate.build_cost_advocate_user_message(state)

    msg = f"## Decision Question\n{state.question}\n"
    if state.context:
        msg += f"\n## Additional Context\n{state.context}\n"
    msg += f"\n## Debate History\n{_format_history(state.rounds)}\n"

    # Moderator guidance from last round
    if state.rounds:
        guidance = state.rounds[-1].moderator.guidance_for_next_round
        if guidance:
            msg += f"\n## Moderator Guidance\n{guidance}\n"

    msg += f"\nThis is round {state.current_round}. Please speak as the Advocate."
    return msg
