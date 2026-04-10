import logging

from maverickj.schemas.debate import DebateState, DebateStatus

logger = logging.getLogger(__name__)


def should_continue(state: DebateState) -> str:
    """LangGraph 的条件边函数: 判断辩论是否继续"""

    # 硬上限
    if state.current_round >= state.config.max_rounds:
        logger.info(f"达到最大轮数 {state.config.max_rounds}，终止辩论")
        state.convergence_reason = f"达到最大轮数限制 ({state.config.max_rounds} 轮)"
        return "terminate"

    # 错误状态
    if state.status == DebateStatus.ERROR:
        logger.info("辩论出错，终止")
        state.convergence_reason = "辩论过程中发生错误"
        return "terminate"

    # Moderator 判定
    if not state.rounds:
        return "continue"

    latest = state.rounds[-1].moderator
    if not latest.should_continue:
        logger.info(f"Moderator 判定终止辩论: score={latest.convergence_score}")
        state.convergence_reason = f"Moderator 判定收敛 (score={latest.convergence_score:.2f})"
        return "terminate"

    # 双重校验：convergence_score 持续高位
    recent_scores = [r.moderator.convergence_score for r in state.rounds[-2:]]
    if (
        len(recent_scores) >= 2
        and all(s >= state.config.convergence_score_target for s in recent_scores)
    ):
        logger.info(f"连续高收敛分数 {recent_scores}，终止辩论")
        state.convergence_reason = f"连续 {len(recent_scores)} 轮收敛分数 >= {state.config.convergence_score_target}"
        return "terminate"

    return "continue"
