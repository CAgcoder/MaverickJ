import logging

from maverickj.agents.fact_checker import FactCheckerAgent
from maverickj.core.argument_registry import ArgumentRegistry
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState

logger = logging.getLogger(__name__)


async def fact_checker_node(state: DebateState, router: ModelRouter) -> dict:
    """Fact-Checker node: fact and logic verification."""
    logger.info(f"=== Round {state.current_round} - Fact-Checker verification ===")

    agent = FactCheckerAgent(router)
    response, usage = await agent.run(state)

    # Update ArgumentRegistry: associate fact-check results with arguments
    registry = ArgumentRegistry(state.argument_registry)
    for check in response.checks:
        registry.add_fact_check(check.target_argument_id, check)

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

    return {
        "current_round_fact_check": response,
        "argument_registry": registry.to_dict(),
        "metadata": state.metadata.model_copy(update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + input_tokens + output_tokens,
        }),
    }
