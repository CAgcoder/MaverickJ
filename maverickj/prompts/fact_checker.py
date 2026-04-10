from maverickj.schemas.agents import AgentResponse
from maverickj.schemas.debate import DebateState


def _format_current_round_arguments(state: DebateState) -> str:
    msg = ""
    if state.current_round_advocate:
        adv = state.current_round_advocate
        msg += "[Advocate's Arguments]\n"
        msg += "\n".join(
            f"- [{a.id}] {a.claim}\n  Reasoning: {a.reasoning}\n  Evidence: {a.evidence or 'none'}\n  Status: {a.status.value}"
            for a in adv.arguments
        )
        msg += f"\nRebuttals: {'; '.join(f'Against {r.target_argument_id}: {r.counter_claim}' for r in adv.rebuttals) or 'none'}\n"

    if state.current_round_critic:
        crt = state.current_round_critic
        msg += "\n[Critic's Arguments]\n"
        msg += "\n".join(
            f"- [{a.id}] {a.claim}\n  Reasoning: {a.reasoning}\n  Evidence: {a.evidence or 'none'}\n  Status: {a.status.value}"
            for a in crt.arguments
        )
        msg += f"\nRebuttals: {'; '.join(f'Against {r.target_argument_id}: {r.counter_claim}' for r in crt.rebuttals) or 'none'}\n"

    return msg


def build_fact_checker_system_prompt(state: DebateState) -> str:
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    return f"""You are a professor of logic acting as a neutral third party to evaluate the logical consistency and factual accuracy of both sides' arguments.

## Your Role
- You are the Fact-Checker. You do not take sides; you only assess argument quality.
- You must output everything in {lang}.

## Behavioral Rules
- Evaluate all active-status arguments and rebuttals from this round.
- For each argument, deliver a verdict:
  - valid: logically consistent and reasonably argued
  - flawed: contains a logical fallacy or reasoning error (specify the exact fallacy type)
  - needs_context: the argument itself is sound but requires critical missing context to hold
  - unverifiable: cannot be judged true or false with the information currently available
- If you detect cognitive biases (confirmation bias, survivorship bias, slippery slope, etc.), explicitly call them out.
- Provide an overall_assessment summarizing the quality of argumentation this round."""


def build_fact_checker_user_message(state: DebateState) -> str:
    msg = f"## Decision Question\n{state.question}\n"
    if state.context:
        msg += f"\n## Additional Context\n{state.context}\n"
    msg += f"\n## Arguments and Rebuttals to Evaluate This Round\n"
    msg += _format_current_round_arguments(state)
    msg += "\nPlease fact-check and logic-check all of the above arguments."
    return msg
