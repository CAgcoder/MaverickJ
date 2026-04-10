import logging

from maverickj.schemas.debate import DebateState, DebateStatus

logger = logging.getLogger(__name__)


def should_continue(state: DebateState) -> str:
    """LangGraph conditional edge function: determines whether the debate should continue."""

    # Hard limit
    if state.current_round >= state.config.max_rounds:
        logger.info(f"Max rounds reached ({state.config.max_rounds}), terminating debate")
        state.convergence_reason = f"Max rounds limit reached ({state.config.max_rounds} rounds)"
        return "terminate"

    # Error state
    if state.status == DebateStatus.ERROR:
        logger.info("Debate encountered an error, terminating")
        state.convergence_reason = "An error occurred during the debate"
        return "terminate"

    # Moderator decision
    if not state.rounds:
        return "continue"

    latest = state.rounds[-1].moderator
    if not latest.should_continue:
        logger.info(f"Moderator decided to terminate: score={latest.convergence_score}")
        state.convergence_reason = f"Moderator determined convergence (score={latest.convergence_score:.2f})"
        return "terminate"

    # Double-check: sustained high convergence score
    recent_scores = [r.moderator.convergence_score for r in state.rounds[-2:]]
    if (
        len(recent_scores) >= 2
        and all(s >= state.config.convergence_score_target for s in recent_scores)
    ):
        logger.info(f"Sustained high convergence scores {recent_scores}, terminating")
        state.convergence_reason = f"{len(recent_scores)} consecutive rounds with convergence score >= {state.config.convergence_score_target}"
        return "terminate"

    return "continue"
