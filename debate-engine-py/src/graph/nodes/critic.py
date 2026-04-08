import logging

from src.agents.critic import CriticAgent
from src.core.argument_registry import ArgumentRegistry
from src.llm.router import ModelRouter
from src.schemas.debate import DebateState

logger = logging.getLogger(__name__)


async def critic_node(state: DebateState, router: ModelRouter) -> dict:
    """Critic node: 反方批评"""
    logger.info(f"=== 第 {state.current_round} 轮 - Critic 发言 ===")

    agent = CriticAgent(router)
    response, usage = await agent.run(state)

    # 更新 ArgumentRegistry
    registry = ArgumentRegistry(state.argument_registry)
    for arg in response.arguments:
        registry.register(arg, state.current_round, "critic")
    for rebuttal in response.rebuttals:
        registry.add_rebuttal(rebuttal.target_argument_id, rebuttal)

    # 处理让步
    for concession in response.concessions:
        for arg_id, record in registry.to_dict().items():
            if record.raised_by == "critic" and concession in record.argument.claim:
                from src.schemas.arguments import ArgumentStatus
                registry.update_status(arg_id, ArgumentStatus.CONCEDED, concession)

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

    return {
        "current_round_critic": response,
        "argument_registry": registry.to_dict(),
        "metadata": state.metadata.model_copy(update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + input_tokens + output_tokens,
        }),
    }
