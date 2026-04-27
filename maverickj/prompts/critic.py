from maverickj.schemas.agents import AgentResponse
from maverickj.schemas.debate import DebateState
from maverickj.prompts.advocate import build_advocate_user_message


def _format_advocate_output(advocate: AgentResponse) -> str:
    args_str = "\n".join(
        f"- [{a.id}] {a.claim} | Reasoning: {a.reasoning} | Evidence: {a.evidence or 'none'} | Status: {a.status.value}"
        for a in advocate.arguments
    )
    rebuttals_str = "\n".join(
        f"- Against {r.target_argument_id}: {r.counter_claim} | {r.reasoning}"
        for r in advocate.rebuttals
    ) or "none"
    concessions_str = "; ".join(advocate.concessions) or "none"

    return (
        f"[Current Round Advocate Arguments]\nArguments:\n{args_str}\n"
        f"Rebuttals:\n{rebuttals_str}\n"
        f"Concessions: {concessions_str}\n"
        f"Confidence Shift: {advocate.confidence_shift}"
    )


def build_critic_system_prompt(state: DebateState) -> str:
    if state.config.mode == "supply_chain":
        from maverickj.supply_chain.prompts import risk_critic

        return risk_critic.build_risk_critic_system_prompt(state)

    current_round = state.current_round
    lang = "Chinese" if state.config.language in ("zh", "auto") else "English"

    return f"""You are a rigorous risk analyst responsible for systematically challenging pro-side arguments and building the con-side case in the debate.

## Your Role
- You are the Critic. Your goal is to identify weaknesses in the Advocate's arguments and construct a strong con-side case.
- You must output everything in {lang}.

## Behavioral Rules
- Each round workflow:
  1. Examine each of the Advocate's arguments; identify logical gaps, hidden assumptions, and missing considerations.
  2. For each argument that warrants a rebuttal, produce a Rebuttal citing the Advocate's specific argument ID (target_argument_id).
  3. Present your own independent con-side arguments.
  4. Respond to the Advocate's rebuttals against your arguments.
- If any of the Advocate's arguments are genuinely unassailable, concede them (add to concessions).
- No sophistry or straw-man fallacies; you must attack the opponent's actual argument.
- New argument ID format: CRT-R{current_round}-01, CRT-R{current_round}-02, ...
- At the end of each round, report confidence_shift: your change in confidence in the con-side position.

## ⚠️ Output Format Requirements
- `arguments` MUST be a JSON **array** of objects, e.g. [{{"id": "CRT-R{current_round}-01", "claim": "...", "reasoning": "...", "status": "active"}}]
- `rebuttals` MUST be a JSON **array** of objects, e.g. [{{"target_argument_id": "ADV-R1-01", "counter_claim": "...", "reasoning": "..."}}]
- `concessions` MUST be a JSON **array** of strings, e.g. ["point A", "point B"]
- **NEVER** serialize any array as a quoted string. Return raw JSON arrays only."""


def build_critic_user_message(state: DebateState) -> str:
    if state.config.mode == "supply_chain":
        from maverickj.supply_chain.prompts import risk_critic

        return risk_critic.build_risk_critic_user_message(state)

    msg = build_advocate_user_message(state)

    if state.current_round_advocate:
        msg += f"\n\n{_format_advocate_output(state.current_round_advocate)}"

    msg += f"\n\nThis is round {state.current_round}. Please speak as the Critic and rebut the Advocate's arguments while presenting your own con-side arguments."
    return msg
