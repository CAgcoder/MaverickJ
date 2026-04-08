import logging

from src.agents.moderator import ModeratorAgent
from src.llm.router import ModelRouter
from src.schemas.debate import DebateRound, DebateState

logger = logging.getLogger(__name__)


async def moderator_node(state: DebateState, router: ModelRouter) -> dict:
    """Moderator node: 主持人裁决，同时组装本轮 DebateRound"""
    logger.info(f"=== 第 {state.current_round} 轮 - Moderator 裁决 ===")

    agent = ModeratorAgent(router)
    response, usage = await agent.run(state)

    # 组装完整的 DebateRound
    current_round = DebateRound(
        round_number=state.current_round,
        advocate=state.current_round_advocate,
        critic=state.current_round_critic,
        fact_check=state.current_round_fact_check,
        moderator=response,
    )

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

    return {
        "current_round_moderator": response,
        "rounds": state.rounds + [current_round],
        "metadata": state.metadata.model_copy(update={
            "total_llm_calls": state.metadata.total_llm_calls + 1,
            "total_tokens_used": state.metadata.total_tokens_used + input_tokens + output_tokens,
        }),
    }
