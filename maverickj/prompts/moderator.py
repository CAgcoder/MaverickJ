from maverickj.schemas.debate import DebateRound, DebateState


def _format_full_transcript(state: DebateState) -> str:
    msg = ""

    # Historical rounds
    for r in state.rounds:
        msg += _format_round(r) + "\n\n"

    # Current round phases completed so far
    msg += f"=== Round {state.current_round} (Current) ===\n"

    if state.current_round_advocate:
        adv = state.current_round_advocate
        msg += "[Advocate's Arguments]\n"
        msg += "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in adv.arguments) + "\n"
        msg += f"Rebuttals: {'; '.join(f'{r.target_argument_id}: {r.counter_claim}' for r in adv.rebuttals) or 'none'}\n"
        msg += f"Concessions: {'; '.join(adv.concessions) or 'none'}\n"
        msg += f"Confidence Shift: {adv.confidence_shift}\n\n"

    if state.current_round_critic:
        crt = state.current_round_critic
        msg += "[Critic's Arguments]\n"
        msg += "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in crt.arguments) + "\n"
        msg += f"Rebuttals: {'; '.join(f'{r.target_argument_id}: {r.counter_claim}' for r in crt.rebuttals) or 'none'}\n"
        msg += f"Concessions: {'; '.join(crt.concessions) or 'none'}\n"
        msg += f"Confidence Shift: {crt.confidence_shift}\n\n"

    if state.current_round_fact_check:
        fc = state.current_round_fact_check
        msg += "[Fact Check]\n"
        msg += "\n".join(f"- {c.target_argument_id}: {c.verdict.value} - {c.explanation}" for c in fc.checks) + "\n"
        msg += f"Overall Assessment: {fc.overall_assessment}\n\n"

    return msg


def _format_round(r: DebateRound) -> str:
    return (
        f"=== Round {r.round_number} ===\n"
        f"[Advocate] {'; '.join(f'[{a.id}] {a.claim} ({a.status.value})' for a in r.advocate.arguments)}\n"
        f"[Critic] {'; '.join(f'[{a.id}] {a.claim} ({a.status.value})' for a in r.critic.arguments)}\n"
        f"[Fact Check] {r.fact_check.overall_assessment}\n"
        f"[Summary] {r.moderator.round_summary}\n"
        f"Convergence Score: {r.moderator.convergence_score}"
    )


def build_moderator_system_prompt(state: DebateState) -> str:
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    return f"""You are the debate Moderator, responsible for controlling the debate pace, judging convergence, and guiding focus.

## Your Role
- You are a neutral debate moderator.
- You must output everything in {lang}.

## Tasks to Complete Each Round
1. Summarize this round's debate progress (round_summary).
2. Identify the most critical unresolved divergences (key_divergences).
3. Calculate a convergence score (convergence_score, 0–1):
   - Is the number of new arguments from both sides decreasing?
   - Are concessions increasing?
   - Are key divergences narrowing?
   - Are both sides' confidence_shift values trending toward 0?
4. Decide whether to continue the debate (should_continue).
5. If continuing, provide focus guidance for the next round (guidance_for_next_round).

## Convergence Rules
- convergence_score >= {state.config.convergence_score_target} and no substantive new arguments for {state.config.convergence_threshold} consecutive rounds → should_continue = false
- Currently at round {state.current_round}; maximum rounds is {state.config.max_rounds}.
- If current round = max rounds → should_continue = false.
- If both sides' confidence shifts are trending toward 0, consider terminating.

## Scoring Anchors
- If this round has only 0–1 new arguments and concessions are increasing, convergence_score should be 0.7–0.9.
- If both sides present many new arguments and rebuttals, convergence_score should be 0.1–0.4.
- If key divergences are narrowing but new refined arguments still emerge, convergence_score should be 0.4–0.7.

## ⚠️ Output Format Requirements
- `key_divergences` MUST be a JSON **array** of strings, e.g. ["divergence 1", "divergence 2"]
- **NEVER** serialize any array as a quoted string. Return raw JSON arrays only."""


def build_moderator_user_message(state: DebateState) -> str:
    msg = f"## Decision Question\n{state.question}\n"
    if state.context:
        msg += f"\n## Additional Context\n{state.context}\n"
    msg += f"\n## Full Debate Transcript\n{_format_full_transcript(state)}\n"
    msg += f"Please deliver your ruling for round {state.current_round}."
    return msg
