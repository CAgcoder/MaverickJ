import logging

from maverickj.agents.advocate import AdvocateAgent
from maverickj.core.argument_registry import ArgumentRegistry
from maverickj.llm.router import ModelRouter
from maverickj.schemas.debate import DebateState

logger = logging.getLogger(__name__)


async def advocate_node(state: DebateState, router: ModelRouter) -> dict:
    """Advocate node: pro-side argumentation."""
    logger.info(f"=== Round {state.current_round} - Advocate turn ===")

    agent = AdvocateAgent(router)
    response, usage, tool_calls_update = await agent.run(state)

    # Update ArgumentRegistry
    registry = ArgumentRegistry(state.argument_registry)
    for arg in response.arguments:
        registry.register(arg, state.current_round, "advocate")
    for rebuttal in response.rebuttals:
        registry.add_rebuttal(rebuttal.target_argument_id, rebuttal)

    # Handle concessions
    for concession in response.concessions:
        # Find the conceded argument (if concession contains an ID)
        for arg_id, record in registry.to_dict().items():
            if record.raised_by == "advocate" and concession in record.argument.claim:
                from maverickj.schemas.arguments import ArgumentStatus
                registry.update_status(arg_id, ArgumentStatus.CONCEDED, concession)

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

    out: dict = {
        "current_round_advocate": response,
        "argument_registry": registry.to_dict(),
        "metadata": state.metadata.model_copy(update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + input_tokens + output_tokens,
        }),
    }
    if tool_calls_update is not None:
        out["tool_calls"] = tool_calls_update
    return out
