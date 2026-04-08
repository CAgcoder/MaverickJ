from src.schemas.debate import DebateState


def build_report_generator_system_prompt(state: DebateState) -> str:
    lang = "中文" if state.config.language in ("zh", "auto") else "English"

    return f"""你是决策报告生成器，负责基于完整的辩论记录生成结构化决策报告。

## 你的任务
基于完整的辩论记录，生成结构化决策报告。你必须用{lang}输出。

## 要求
1. executive_summary：用 3-5 句话概括辩论结论
2. recommendation：给出建议方向、置信度、前提条件
   - 置信度基于：正方存活论点强度 vs 反方存活论点强度
   - 如果双方势均力敌，置信度为 "low"，建议 "需要更多信息"
3. pro_arguments / con_arguments：
   - 只包含 status 为 "active" 或 "modified" 的论点
   - 按 strength 降序排列
   - strength 评分规则：基础分 5，每经受一次反驳仍存活 +1，Fact-Checker 评为 valid 额外 +1，评为 flawed 则 -3
4. unresolved_disagreements：标记辩论中始终无法达成共识的核心问题
5. next_steps：基于 unresolved_disagreements 建议具体的后续调研行动，不允许"需要进一步研究"这种空话"""


def build_report_generator_user_message(state: DebateState) -> str:
    msg = f"## 决策问题\n{state.question}\n"
    if state.context:
        msg += f"\n## 补充背景\n{state.context}\n"
    msg += "\n## 完整辩论记录\n"

    for r in state.rounds:
        msg += f"\n### 第 {r.round_number} 轮\n"

        # Advocate
        msg += "**正方论证：**\n"
        for a in r.advocate.arguments:
            msg += f"- [{a.id}] {a.claim}\n  推理: {a.reasoning}\n  证据: {a.evidence or '无'}\n  状态: {a.status.value}\n"
        msg += f"反驳: {'; '.join(f'{rb.target_argument_id}: {rb.counter_claim}' for rb in r.advocate.rebuttals) or '无'}\n"
        msg += f"让步: {'; '.join(r.advocate.concessions) or '无'}\n"
        msg += f"信心变化: {r.advocate.confidence_shift}\n\n"

        # Critic
        msg += "**反方论证：**\n"
        for a in r.critic.arguments:
            msg += f"- [{a.id}] {a.claim}\n  推理: {a.reasoning}\n  证据: {a.evidence or '无'}\n  状态: {a.status.value}\n"
        msg += f"反驳: {'; '.join(f'{rb.target_argument_id}: {rb.counter_claim}' for rb in r.critic.rebuttals) or '无'}\n"
        msg += f"让步: {'; '.join(r.critic.concessions) or '无'}\n"
        msg += f"信心变化: {r.critic.confidence_shift}\n\n"

        # Fact Check
        msg += "**事实校验：**\n"
        for c in r.fact_check.checks:
            msg += f"- {c.target_argument_id}: {c.verdict.value} — {c.explanation}\n"
            if c.correction:
                msg += f"  修正: {c.correction}\n"
        msg += f"总体评估: {r.fact_check.overall_assessment}\n\n"

        # Moderator
        msg += "**主持人裁决：**\n"
        msg += f"总结: {r.moderator.round_summary}\n"
        msg += f"关键分歧: {'; '.join(r.moderator.key_divergences)}\n"
        msg += f"收敛分数: {r.moderator.convergence_score}\n"
        msg += f"是否继续: {r.moderator.should_continue}\n"
        if r.moderator.guidance_for_next_round:
            msg += f"下轮引导: {r.moderator.guidance_for_next_round}\n"

    msg += f"\n## 辩论终止状态: {state.status.value}"
    if state.convergence_reason:
        msg += f"\n收敛原因: {state.convergence_reason}"
    msg += f"\n总 LLM 调用: {state.metadata.total_llm_calls}"
    msg += f"\n总 token 消耗: {state.metadata.total_tokens_used}"

    msg += "\n\n请基于以上辩论记录生成决策报告。"
    return msg
