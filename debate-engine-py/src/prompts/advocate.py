from src.schemas.debate import DebateRound, DebateState


def _format_history(rounds: list[DebateRound]) -> str:
    if not rounds:
        return "（尚无历史辩论记录）"
    parts = []
    for r in rounds:
        adv = r.advocate
        crt = r.critic
        fc = r.fact_check
        mod = r.moderator
        parts.append(
            f"=== 第 {r.round_number} 轮 ===\n"
            f"【正方论证】\n"
            + "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in adv.arguments)
            + f"\n反驳: {'; '.join(f'针对{rb.target_argument_id}: {rb.counter_claim}' for rb in adv.rebuttals) or '无'}"
            f"\n让步: {'; '.join(adv.concessions) or '无'}"
            f"\n信心变化: {adv.confidence_shift}"
            f"\n\n【反方批评】\n"
            + "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in crt.arguments)
            + f"\n反驳: {'; '.join(f'针对{rb.target_argument_id}: {rb.counter_claim}' for rb in crt.rebuttals) or '无'}"
            f"\n让步: {'; '.join(crt.concessions) or '无'}"
            f"\n信心变化: {crt.confidence_shift}"
            f"\n\n【事实校验】\n"
            + "\n".join(f"- {c.target_argument_id}: {c.verdict.value} - {c.explanation}" for c in fc.checks)
            + f"\n总体评估: {fc.overall_assessment}"
            f"\n\n【主持人总结】\n{mod.round_summary}"
            f"\n关键分歧: {'; '.join(mod.key_divergences)}"
            f"\n收敛分数: {mod.convergence_score}"
        )
    return "\n\n".join(parts)


def build_advocate_system_prompt(state: DebateState) -> str:
    current_round = state.current_round
    lang = "中文" if state.config.language in ("zh", "auto") else "English"

    if current_round == 1:
        round_rules = f"""- 这是第一轮辩论，请独立提出 3-5 个核心正方论点
- 每个论点必须有清晰的主张（claim）、推理过程（reasoning）和支撑证据（evidence）
- 论点 ID 格式：ADV-R{current_round}-01, ADV-R{current_round}-02, ..."""
    else:
        round_rules = f"""- 这是第 {current_round} 轮辩论，你已经看到了之前的辩论记录
- 你需要回应 Critic 的反驳和 Fact-Checker 的校验结果
- 对被有效反驳的论点：修正立场或承认让步（放入 concessions）
- 对被部分反驳的论点：补充论证、修正措辞（将论点状态改为 modified）
- 可以引入新论点来强化正方整体论证
- 对 Critic 的论点提出你自己的反驳（rebuttals），需引用对方论点 ID（target_argument_id）
- 新论点 ID 格式：ADV-R{current_round}-01, ADV-R{current_round}-02, ..."""

    return f"""你是一位资深的商业战略顾问，负责在辩论中论证正方立场（即"应该做"的方向）。

## 你的角色
- 你是正方论证者（Advocate），你的目标是为决策问题构建最强的正方论证
- 你必须用{lang}输出所有内容

## 行为规则
{round_rules}
- 每轮结束报告 confidence_shift：你对正方立场的信心变化（-1 到 1 之间，负数表示信心降低）
- 禁止无视对方有效反驳
- 禁止重复已被推翻的论点
- 只有当对方论证确实无懈可击时才承认让步"""


def build_advocate_user_message(state: DebateState) -> str:
    msg = f"## 决策问题\n{state.question}\n"
    if state.context:
        msg += f"\n## 补充背景\n{state.context}\n"
    msg += f"\n## 辩论历史\n{_format_history(state.rounds)}\n"

    # Moderator guidance from last round
    if state.rounds:
        guidance = state.rounds[-1].moderator.guidance_for_next_round
        if guidance:
            msg += f"\n## 主持人引导\n{guidance}\n"

    msg += f"\n当前是第 {state.current_round} 轮辩论。请以正方论证者的身份发言。"
    return msg
