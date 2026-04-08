from src.schemas.debate import DebateState


def build_report_generator_system_prompt(state: DebateState) -> str:
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    return f"""You are a decision report generator. Your task is to produce a structured decision report based on the complete debate transcript.

## Your Task
Generate a structured decision report from the full debate record. You must output in {lang}.

## Requirements
1. executive_summary: Summarize the debate conclusion in 3–5 sentences.
2. recommendation: Provide a recommended direction, confidence level, and preconditions.
   - Base confidence on: strength of surviving pro-side arguments vs. con-side arguments.
   - If both sides are evenly matched, confidence = "low" and recommendation = "more information needed".
3. pro_arguments / con_arguments:
   - Include only arguments with status "active" or "modified".
   - Sort by strength in descending order.
   - Strength scoring rules: base score 5; +1 for each rebuttal survived; +1 if Fact-Checker rated "valid"; -3 if rated "flawed".
4. unresolved_disagreements: Mark core issues where no consensus was reached throughout the debate.
5. next_steps: Suggest concrete follow-up research actions based on unresolved_disagreements. Vague phrases like "further research is needed" are not allowed.

## Output Format
You MUST output a single valid JSON object that strictly conforms to the required schema. Do NOT use XML tags or any other format. All nested objects (recommendation, debate_stats, etc.) must be proper JSON objects, not strings."""


def build_report_generator_user_message(state: DebateState) -> str:
    msg = f"## Decision Question\n{state.question}\n"
    if state.context:
        msg += f"\n## Additional Context\n{state.context}\n"
    msg += "\n## Full Debate Transcript\n"

    for r in state.rounds:
        msg += f"\n### Round {r.round_number}\n"

        # Advocate
        msg += "**Advocate's Arguments:**\n"
        for a in r.advocate.arguments:
            msg += f"- [{a.id}] {a.claim}\n  Reasoning: {a.reasoning}\n  Evidence: {a.evidence or 'none'}\n  Status: {a.status.value}\n"
        msg += f"Rebuttals: {'; '.join(f'{rb.target_argument_id}: {rb.counter_claim}' for rb in r.advocate.rebuttals) or 'none'}\n"
        msg += f"Concessions: {'; '.join(r.advocate.concessions) or 'none'}\n"
        msg += f"Confidence Shift: {r.advocate.confidence_shift}\n\n"

        # Critic
        msg += "**Critic's Arguments:**\n"
        for a in r.critic.arguments:
            msg += f"- [{a.id}] {a.claim}\n  Reasoning: {a.reasoning}\n  Evidence: {a.evidence or 'none'}\n  Status: {a.status.value}\n"
        msg += f"Rebuttals: {'; '.join(f'{rb.target_argument_id}: {rb.counter_claim}' for rb in r.critic.rebuttals) or 'none'}\n"
        msg += f"Concessions: {'; '.join(r.critic.concessions) or 'none'}\n"
        msg += f"Confidence Shift: {r.critic.confidence_shift}\n\n"

        # Fact Check
        msg += "**Fact Check:**\n"
        for c in r.fact_check.checks:
            msg += f"- {c.target_argument_id}: {c.verdict.value} — {c.explanation}\n"
            if c.correction:
                msg += f"  Correction: {c.correction}\n"
        msg += f"Overall Assessment: {r.fact_check.overall_assessment}\n\n"

        # Moderator
        msg += "**Moderator's Ruling:**\n"
        msg += f"Summary: {r.moderator.round_summary}\n"
        msg += f"Key Divergences: {'; '.join(r.moderator.key_divergences)}\n"
        msg += f"Convergence Score: {r.moderator.convergence_score}\n"
        msg += f"Continue: {r.moderator.should_continue}\n"
        if r.moderator.guidance_for_next_round:
            msg += f"Next Round Guidance: {r.moderator.guidance_for_next_round}\n"

    msg += f"\n## Debate Termination Status: {state.status.value}"
    if state.convergence_reason:
        msg += f"\nConvergence Reason: {state.convergence_reason}"
    msg += f"\nTotal LLM Calls: {state.metadata.total_llm_calls}"
    msg += f"\nTotal Tokens Used: {state.metadata.total_tokens_used}"

    msg += "\n\nPlease generate the decision report based on the above debate transcript."
    return msg
