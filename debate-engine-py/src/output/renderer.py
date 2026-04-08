from src.schemas.debate import DebateState
from src.schemas.report import DecisionReport


def render_report_to_markdown(report: DecisionReport, state: DebateState) -> str:
    """将 DecisionReport 渲染为 Markdown"""
    lines = []

    # Header
    lines.append(f"# 决策分析报告")
    lines.append("")
    lines.append(f"**决策问题：** {report.question}")
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
