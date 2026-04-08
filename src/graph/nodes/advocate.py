import logging

from src.agents.advocate import AdvocateAgent
from src.core.argument_registry import ArgumentRegistry
from src.llm.router import ModelRouter
from src.schemas.debate import DebateState

logger = logging.getLogger(__name__)


async def advocate_node(state: DebateState, router: ModelRouter) -> dict:
    """Advocate node: 正方论证"""
    logger.info(f"=== 第 {state.current_round} 轮 - Advocate 发言 ===")

    agent = AdvocateAgent(router)
    response, usage = await agent.run(state)

    # 更新 ArgumentRegistry
    registry = ArgumentRegistry(state.argument_registry)
    for arg in response.arguments:
        registry.register(arg, state.current_round, "advocate")
    for rebuttal in response.rebuttals:
        registry.add_rebuttal(rebuttal.target_argument_id, rebuttal)

    # 处理让步
    for concession in response.concessions:
        # 找到被让步的论点（如果 concession 包含 ID）
        for arg_id, record in registry.to_dict().items():
            if record.raised_by == "advocate" and concession in record.argument.claim:
                from src.schemas.arguments import ArgumentStatus
                registry.update_status(arg_id, ArgumentStatus.CONCEDED, concession)

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

    return {
        "current_round_advocate": response,
        "argument_registry": registry.to_dict(),
        "metadata": state.metadata.model_copy(update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + input_tokens + output_tokens,
        }),
    }
