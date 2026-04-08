from src.schemas.debate import DebateRound, DebateState


def _format_full_transcript(state: DebateState) -> str:
    msg = ""

    # Historical rounds
    for r in state.rounds:
        msg += _format_round(r) + "\n\n"

    # Current round phases completed so far
    msg += f"=== 第 {state.current_round} 轮（当前轮）===\n"

    if state.current_round_advocate:
        adv = state.current_round_advocate
        msg += "【正方论证】\n"
        msg += "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in adv.arguments) + "\n"
        msg += f"反驳: {'; '.join(f'{r.target_argument_id}: {r.counter_claim}' for r in adv.rebuttals) or '无'}\n"
        msg += f"让步: {'; '.join(adv.concessions) or '无'}\n"
        msg += f"信心变化: {adv.confidence_shift}\n\n"

    if state.current_round_critic:
        crt = state.current_round_critic
        msg += "【反方论证】\n"
        msg += "\n".join(f"- [{a.id}] {a.claim} ({a.status.value})" for a in crt.arguments) + "\n"
        msg += f"反驳: {'; '.join(f'{r.target_argument_id}: {r.counter_claim}' for r in crt.rebuttals) or '无'}\n"
        msg += f"让步: {'; '.join(crt.concessions) or '无'}\n"
        msg += f"信心变化: {crt.confidence_shift}\n\n"

    if state.current_round_fact_check:
        fc = state.current_round_fact_check
        msg += "【事实校验】\n"
        msg += "\n".join(f"- {c.target_argument_id}: {c.verdict.value} - {c.explanation}" for c in fc.checks) + "\n"
        msg += f"总体评估: {fc.overall_assessment}\n\n"

    return msg


def _format_round(r: DebateRound) -> str:
    return (
        f"=== 第 {r.round_number} 轮 ===\n"
        f"【正方】{'; '.join(f'[{a.id}] {a.claim} ({a.status.value})' for a in r.advocate.arguments)}\n"
        f"【反方】{'; '.join(f'[{a.id}] {a.claim} ({a.status.value})' for a in r.critic.arguments)}\n"
        f"【校验】{r.fact_check.overall_assessment}\n"
        f"【总结】{r.moderator.round_summary}\n"
        f"收敛分数: {r.moderator.convergence_score}"
    )


def build_moderator_system_prompt(state: DebateState) -> str:
    lang = "中文" if state.config.language in ("zh", "auto") else "English"

    return f"""你是辩论主持人（Moderator），负责控制辩论节奏、判断收敛、引导焦点。

## 你的角色
- 你是中立的辩论主持人
- 你必须用{lang}输出所有内容

## 每轮你需要完成的工作
1. 总结本轮辩论进展（round_summary）
2. 识别当前最关键的未解决分歧（key_divergences）
3. 计算收敛分数（convergence_score，0-1）：
   - 双方新论点数量是否递减
   - 让步（concessions）是否增加
   - 关键分歧是否在收窄
   - 双方 confidence_shift 的绝对值是否趋于 0
4. 判断是否应该继续辩论（should_continue）
5. 如果继续，给出下一轮的焦点引导（guidance_for_next_round）

## 收敛判定规则
- convergence_score >= {state.config.convergence_score_target} 且连续 {state.config.convergence_threshold} 轮无实质性新论点 → should_continue = false
- 当前已到第 {state.current_round} 轮，最大轮数为 {state.config.max_rounds}
- 如果当前轮 = 最大轮数 → should_continue = false
- 双方信心变化都趋于 0 → 可以考虑终止

## 评分锚点
- 如果本轮只有 0-1 个新论点，且 concessions 数量增加，convergence_score 应在 0.7-0.9 之间
- 如果双方都提出大量新论点和反驳，convergence_score 应在 0.1-0.4 之间
- 如果关键分歧在收窄但仍有新的细化论点，convergence_score 应在 0.4-0.7 之间"""


def build_moderator_user_message(state: DebateState) -> str:
    msg = f"## 决策问题\n{state.question}\n"
    if state.context:
        msg += f"\n## 补充背景\n{state.context}\n"
    msg += f"\n## 完整辩论记录\n{_format_full_transcript(state)}\n"
    msg += f"请对第 {state.current_round} 轮辩论做出裁决。"
    return msg
