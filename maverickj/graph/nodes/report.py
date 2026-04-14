import logging
from datetime import datetime

from maverickj.agents.base import BaseAgent
from maverickj.core.argument_registry import ArgumentRegistry
from maverickj.llm.router import ModelRouter
from maverickj.prompts.report_generator import (
    build_report_generator_system_prompt,
    build_report_generator_user_message,
)
from maverickj.schemas.debate import DebateState, DebateStatus
from maverickj.schemas.report import DebateStats, DecisionReport

logger = logging.getLogger(__name__)


async def report_node(state: DebateState, router: ModelRouter) -> dict:
    """Report node: generate the final decision report."""
    logger.info("=== Generating decision report ===")

    agent = BaseAgent(router)
    agent.role = "report_generator"

    system_prompt = build_report_generator_system_prompt(state)
    user_message = build_report_generator_user_message(state)

    response, usage = await agent.invoke(system_prompt, user_message, DecisionReport)

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
    new_total_tokens = state.metadata.total_tokens_used + input_tokens + output_tokens

    # Compute debate_stats from actual state — never rely on the LLM to produce this
    registry = ArgumentRegistry(state.argument_registry)
    stats = registry.get_survivor_stats()
    debate_stats = DebateStats(
        total_rounds=state.current_round,
        arguments_raised=stats["total_raised"],
        arguments_survived=stats["survived"],
        convergence_achieved=(state.status != DebateStatus.MAX_ROUNDS),
        total_tokens=new_total_tokens,
        total_cost_usd=state.metadata.total_cost_usd,
    )
    report_with_stats: DecisionReport = response.model_copy(update={"debate_stats": debate_stats})

    # Determine final status
    if state.current_round >= state.config.max_rounds:
        status = DebateStatus.MAX_ROUNDS
    else:
        status = DebateStatus.CONVERGED

    return {
        "final_report": report_with_stats,
        "status": status,
        "metadata": state.metadata.model_copy(update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": new_total_tokens,
            "completed_at": datetime.now(),
        }),
    }
