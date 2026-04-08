from src.schemas.agents import AgentResponse
from src.schemas.debate import DebateState
from src.prompts.advocate import build_advocate_user_message


def _format_advocate_output(advocate: AgentResponse) -> str:
    args_str = "\n".join(
        f"- [{a.id}] {a.claim} | 推理: {a.reasoning} | 证据: {a.evidence or '无'} | 状态: {a.status.value}"
        for a in advocate.arguments
    )
    rebuttals_str = "\n".join(
        f"- 针对 {r.target_argument_id}: {r.counter_claim} | {r.reasoning}"
        for r in advocate.rebuttals
    ) or "无"
    concessions_str = "; ".join(advocate.concessions) or "无"

    return (
        f"【本轮正方论证】\n论点:\n{args_str}\n"
        f"反驳:\n{rebuttals_str}\n"
        f"让步: {concessions_str}\n"
        f"信心变化: {advocate.confidence_shift}"
    )


def build_critic_system_prompt(state: DebateState) -> str:
    current_round = state.current_round
    lang = "中文" if state.config.language in ("zh", "auto") else "English"

    return f"""你是一位严苛的风险分析师，负责在辩论中系统性地挑战正方论点，构建反方论证。

## 你的角色
- 你是反方批评者（Critic），你的目标是找出正方论证的漏洞并构建反方论证
- 你必须用{lang}输出所有内容

## 行为规则
- 每轮工作流：
  1. 逐条审视 Advocate 的论点，找出逻辑漏洞、隐含假设、缺失考量
  2. 对每个需要反驳的论点产出 rebuttal，必须引用 Advocate 的具体论点 ID（target_argument_id）
  3. 提出自己独立的反方论点（arguments）
  4. 对 Advocate 的反驳做回应
- 如果 Advocate 的某个论点确实无懈可击，承认之（放入 concessions）
- 禁止诡辩、稻草人谬误；必须攻击对方的真实论点
- 新论点 ID 格式：CRT-R{current_round}-01, CRT-R{current_round}-02, ...
- 每轮结束报告 confidence_shift：你对反方立场的信心变化"""


def build_critic_user_message(state: DebateState) -> str:
    msg = build_advocate_user_message(state)

    if state.current_round_advocate:
        msg += f"\n\n{_format_advocate_output(state.current_round_advocate)}"

    msg += f"\n\n当前是第 {state.current_round} 轮辩论。请以反方批评者的身份发言，针对正方的论点进行反驳并提出反方论点。"
    return msg
