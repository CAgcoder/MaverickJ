from maverickj.schemas.debate import DebateState
from maverickj.schemas.report import DecisionReport


def _render_transcript(state: DebateState) -> list[str]:
    """渲染完整辩论记录"""
    lines = []

    lines.append("# 第一部分：完整辩论记录")
    lines.append("")

    if state.context:
        lines.append("## 背景信息")
        lines.append("")
        lines.append(state.context)
        lines.append("")

    for r in state.rounds:
        lines.append(f"---")
        lines.append("")
        lines.append(f"## 第 {r.round_number} 轮辩论")
        lines.append("")

        # Advocate
        lines.append("### 🟢 正方论证者")
        lines.append("")
        for arg in r.advocate.arguments:
            status_icon = "✅" if arg.status.value == "active" else "🔄" if arg.status.value == "modified" else "❌"
            lines.append(f"**{status_icon} [{arg.id}] {arg.claim}**")
            lines.append("")
            lines.append(f"> **推理：** {arg.reasoning}")
            if arg.evidence:
                lines.append(f">")
                lines.append(f"> **证据：** {arg.evidence}")
            lines.append("")
        if r.advocate.rebuttals:
            lines.append("**反驳：**")
            lines.append("")
            for rb in r.advocate.rebuttals:
                lines.append(f"- 针对 **{rb.target_argument_id}**：{rb.counter_claim}")
                lines.append(f"  - 推理：{rb.reasoning}")
            lines.append("")
        if r.advocate.concessions:
            lines.append("**让步：**")
            lines.append("")
            for c in r.advocate.concessions:
                lines.append(f"- 🤝 {c}")
            lines.append("")
        shift = r.advocate.confidence_shift
        shift_label = f"+{shift:.2f}" if shift > 0 else f"{shift:.2f}"
        lines.append(f"*信心变化：{shift_label}*")
        lines.append("")

        # Critic
        lines.append("### 🔴 反方批评者")
        lines.append("")
        for arg in r.critic.arguments:
            status_icon = "✅" if arg.status.value == "active" else "🔄" if arg.status.value == "modified" else "❌"
            lines.append(f"**{status_icon} [{arg.id}] {arg.claim}**")
            lines.append("")
            lines.append(f"> **推理：** {arg.reasoning}")
            if arg.evidence:
                lines.append(f">")
                lines.append(f"> **证据：** {arg.evidence}")
            lines.append("")
        if r.critic.rebuttals:
            lines.append("**反驳：**")
            lines.append("")
            for rb in r.critic.rebuttals:
                lines.append(f"- 针对 **{rb.target_argument_id}**：{rb.counter_claim}")
                lines.append(f"  - 推理：{rb.reasoning}")
            lines.append("")
        if r.critic.concessions:
            lines.append("**让步：**")
            lines.append("")
            for c in r.critic.concessions:
                lines.append(f"- 🤝 {c}")
            lines.append("")
        shift = r.critic.confidence_shift
        shift_label = f"+{shift:.2f}" if shift > 0 else f"{shift:.2f}"
        lines.append(f"*信心变化：{shift_label}*")
        lines.append("")

        # Fact-Checker
        lines.append("### 🔍 事实校验者")
        lines.append("")
        verdict_icons = {
            "valid": "✅",
            "flawed": "❌",
            "needs_context": "⚠️",
            "unverifiable": "❓",
        }
        for check in r.fact_check.checks:
            icon = verdict_icons.get(check.verdict.value, "•")
            lines.append(f"- {icon} **[{check.target_argument_id}]** {check.verdict.value.upper()}")
            lines.append(f"  - {check.explanation}")
            if check.correction:
                lines.append(f"  - 修正建议：{check.correction}")
            if check.fallacy_type:
                lines.append(f"  - 谬误类型：{check.fallacy_type}")
        lines.append("")
        lines.append(f"**整体评估：** {r.fact_check.overall_assessment}")
        lines.append("")

        # Moderator
        lines.append("### ⚖️ 主持人裁决")
        lines.append("")
        lines.append(f"**本轮总结：** {r.moderator.round_summary}")
        lines.append("")
        if r.moderator.key_divergences:
            lines.append("**关键分歧：**")
            lines.append("")
            for d in r.moderator.key_divergences:
                lines.append(f"- {d}")
            lines.append("")
        score = r.moderator.convergence_score
        bar_len = 20
        filled = int(score * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"**收敛分数：** `{bar}` {score:.0%}")
        lines.append("")
        continue_text = "✅ 继续辩论" if r.moderator.should_continue else "🛑 终止辩论"
        lines.append(f"**裁决：** {continue_text}")
        if r.moderator.guidance_for_next_round:
            lines.append("")
            lines.append(f"**下轮焦点：** {r.moderator.guidance_for_next_round}")
        lines.append("")

    # Termination info
    lines.append("---")
    lines.append("")
    status_labels = {
        "converged": "✅ 辩论收敛",
        "max_rounds": "⏱️ 达到最大轮数",
        "error": "❌ 辩论出错",
    }
    lines.append(f"**辩论终止：** {status_labels.get(state.status.value, state.status.value)}")
    if state.convergence_reason:
        lines.append(f"**终止原因：** {state.convergence_reason}")
    lines.append("")

    return lines


def render_report_to_markdown(report: DecisionReport, state: DebateState) -> str:
    """将 DecisionReport 渲染为 Markdown（含完整辩论记录 + 总结分析）"""
    lines = []

    # Report header
    lines.append(f"# 决策分析报告")
    lines.append("")
    lines.append(f"**决策问题：** {report.question}")
    lines.append("")

    # === Part 1: Full Debate Transcript ===
    lines.extend(_render_transcript(state))

    # === Part 2: Analysis ===
    lines.append("---")
    lines.append("")
    lines.append("# 第二部分：总结分析")
    lines.append("")

    # Executive Summary
    lines.append("## 执行摘要")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")

    # Recommendation
    lines.append("## 建议")
    lines.append("")
    confidence_map = {"high": "🟢 高", "medium": "🟡 中", "low": "🔴 低"}
    confidence_label = confidence_map.get(report.recommendation.confidence.value, report.recommendation.confidence.value)
    lines.append(f"**方向：** {report.recommendation.direction}")
    lines.append("")
    lines.append(f"**置信度：** {confidence_label}")
    lines.append("")
    if report.recommendation.conditions:
        lines.append("**前提条件：**")
        for cond in report.recommendation.conditions:
            lines.append(f"- {cond}")
        lines.append("")

    # Pro Arguments
    lines.append("## 正方论点（按强度排序）")
    lines.append("")
    if report.pro_arguments:
        for i, arg in enumerate(report.pro_arguments, 1):
            lines.append(f"### {i}. {arg.claim}")
            lines.append("")
            lines.append(f"- **强度：** {arg.strength}/10")
            lines.append(f"- **经受挑战次数：** {arg.survived_challenges}")
            if arg.modifications:
                lines.append(f"- **修正历史：**")
                for mod in arg.modifications:
                    lines.append(f"  - {mod}")
            if arg.supporting_evidence:
                lines.append(f"- **支撑证据：** {arg.supporting_evidence}")
            lines.append("")
    else:
        lines.append("*无存活论点*")
        lines.append("")

    # Con Arguments
    lines.append("## 反方论点（按强度排序）")
    lines.append("")
    if report.con_arguments:
        for i, arg in enumerate(report.con_arguments, 1):
            lines.append(f"### {i}. {arg.claim}")
            lines.append("")
            lines.append(f"- **强度：** {arg.strength}/10")
            lines.append(f"- **经受挑战次数：** {arg.survived_challenges}")
            if arg.modifications:
                lines.append(f"- **修正历史：**")
                for mod in arg.modifications:
                    lines.append(f"  - {mod}")
            if arg.supporting_evidence:
                lines.append(f"- **支撑证据：** {arg.supporting_evidence}")
            lines.append("")
    else:
        lines.append("*无存活论点*")
        lines.append("")

    # Resolved Disagreements
    if report.resolved_disagreements:
        lines.append("## 已解决的分歧")
        lines.append("")
        for item in report.resolved_disagreements:
            lines.append(f"- {item}")
        lines.append("")

    # Unresolved Disagreements
    if report.unresolved_disagreements:
        lines.append("## 未解决的分歧")
        lines.append("")
        for item in report.unresolved_disagreements:
            lines.append(f"- {item}")
        lines.append("")

    # Risk Factors
    if report.risk_factors:
        lines.append("## 风险因素")
        lines.append("")
        for item in report.risk_factors:
            lines.append(f"- {item}")
        lines.append("")

    # Next Steps
    if report.next_steps:
        lines.append("## 后续行动")
        lines.append("")
        for i, step in enumerate(report.next_steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    # Debate Stats
    lines.append("## 辩论统计")
    lines.append("")
    stats = report.debate_stats
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总轮数 | {stats.total_rounds} |")
    lines.append(f"| 提出论点数 | {stats.arguments_raised} |")
    lines.append(f"| 存活论点数 | {stats.arguments_survived} |")
    lines.append(f"| 是否收敛 | {'是' if stats.convergence_achieved else '否'} |")
    if stats.total_tokens:
        lines.append(f"| Token 消耗 | {stats.total_tokens:,} |")
    if stats.total_cost_usd:
        lines.append(f"| 预估成本 | ${stats.total_cost_usd:.4f} |")
    lines.append("")

    return "\n".join(lines)
