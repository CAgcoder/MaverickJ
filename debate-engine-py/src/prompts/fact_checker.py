from src.schemas.agents import AgentResponse
from src.schemas.debate import DebateState


def _format_current_round_arguments(state: DebateState) -> str:
    msg = ""
    if state.current_round_advocate:
        adv = state.current_round_advocate
        msg += "【正方论证（Advocate）】\n"
        msg += "\n".join(
            f"- [{a.id}] {a.claim}\n  推理: {a.reasoning}\n  证据: {a.evidence or '无'}\n  状态: {a.status.value}"
            for a in adv.arguments
        )
        msg += f"\n反驳: {'; '.join(f'针对{r.target_argument_id}: {r.counter_claim}' for r in adv.rebuttals) or '无'}\n"

    if state.current_round_critic:
        crt = state.current_round_critic
        msg += "\n【反方论证（Critic）】\n"
        msg += "\n".join(
            f"- [{a.id}] {a.claim}\n  推理: {a.reasoning}\n  证据: {a.evidence or '无'}\n  状态: {a.status.value}"
            for a in crt.arguments
        )
        msg += f"\n反驳: {'; '.join(f'针对{r.target_argument_id}: {r.counter_claim}' for r in crt.rebuttals) or '无'}\n"

    return msg


def build_fact_checker_system_prompt(state: DebateState) -> str:
    lang = "中文" if state.config.language in ("zh", "auto") else "English"

    return f"""你是一位逻辑学教授，作为中立第三方审视双方论证的逻辑一致性和事实准确性。

## 你的角色
- 你是事实校验者（Fact-Checker），你不选边站，只评估论证质量
- 你必须用{lang}输出所有内容

## 行为规则
- 对本轮所有 active 状态的论点和反驳进行校验
- 对每个论点给出判定：
  - valid：逻辑自洽、推理合理
  - flawed：存在逻辑谬误或推理错误（指出具体谬误类型）
  - needs_context：论点本身合理但缺少关键上下文才能成立
  - unverifiable：无法在当前信息下判断对错
- 如果发现某方使用了认知偏误（确认偏误、幸存者偏误、滑坡谬误等），明确指出
- 给出整体评估（overall_assessment），概括本轮论证质量"""


def build_fact_checker_user_message(state: DebateState) -> str:
    msg = f"## 决策问题\n{state.question}\n"
    if state.context:
        msg += f"\n## 补充背景\n{state.context}\n"
    msg += f"\n## 本轮需要校验的论点和反驳\n"
    msg += _format_current_round_arguments(state)
    msg += "\n请对以上所有论点进行事实和逻辑校验。"
    return msg
