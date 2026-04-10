from maverickj.schemas.debate import DebateState
from maverickj.schemas.report import DecisionReport


def _render_transcript(state: DebateState) -> list[str]:
    """Render the full debate transcript."""
    lines = []

    lines.append("# Part 1: Full Debate Transcript")
    lines.append("")

    if state.context:
        lines.append("## Background")
        lines.append("")
        lines.append(state.context)
        lines.append("")

    for r in state.rounds:
        lines.append(f"---")
        lines.append("")
        lines.append(f"## Round {r.round_number}")
        lines.append("")

        # Advocate
        lines.append("### 🟢 Advocate")
        lines.append("")
        for arg in r.advocate.arguments:
            status_icon = "✅" if arg.status.value == "active" else "🔄" if arg.status.value == "modified" else "❌"
            lines.append(f"**{status_icon} [{arg.id}] {arg.claim}**")
            lines.append("")
            lines.append(f"> **Reasoning:** {arg.reasoning}")
            if arg.evidence:
                lines.append(f">")
                lines.append(f"> **Evidence:** {arg.evidence}")
            lines.append("")
        if r.advocate.rebuttals:
            lines.append("**Rebuttals:**")
            lines.append("")
            for rb in r.advocate.rebuttals:
                lines.append(f"- Against **{rb.target_argument_id}**: {rb.counter_claim}")
                lines.append(f"  - Reasoning: {rb.reasoning}")
            lines.append("")
        if r.advocate.concessions:
            lines.append("**Concessions:**")
            lines.append("")
            for c in r.advocate.concessions:
                lines.append(f"- 🤝 {c}")
            lines.append("")
        shift = r.advocate.confidence_shift
        shift_label = f"+{shift:.2f}" if shift > 0 else f"{shift:.2f}"
        lines.append(f"*Confidence Shift: {shift_label}*")
        lines.append("")

        # Critic
        lines.append("### 🔴 Critic")
        lines.append("")
        for arg in r.critic.arguments:
            status_icon = "✅" if arg.status.value == "active" else "🔄" if arg.status.value == "modified" else "❌"
            lines.append(f"**{status_icon} [{arg.id}] {arg.claim}**")
            lines.append("")
            lines.append(f"> **Reasoning:** {arg.reasoning}")
            if arg.evidence:
                lines.append(f">")
                lines.append(f"> **Evidence:** {arg.evidence}")
            lines.append("")
        if r.critic.rebuttals:
            lines.append("**Rebuttals:**")
            lines.append("")
            for rb in r.critic.rebuttals:
                lines.append(f"- Against **{rb.target_argument_id}**: {rb.counter_claim}")
                lines.append(f"  - Reasoning: {rb.reasoning}")
            lines.append("")
        if r.critic.concessions:
            lines.append("**Concessions:**")
            lines.append("")
            for c in r.critic.concessions:
                lines.append(f"- 🤝 {c}")
            lines.append("")
        shift = r.critic.confidence_shift
        shift_label = f"+{shift:.2f}" if shift > 0 else f"{shift:.2f}"
        lines.append(f"*Confidence Shift: {shift_label}*")
        lines.append("")

        # Fact-Checker
        lines.append("### 🔍 Fact-Checker")
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
                lines.append(f"  - Correction: {check.correction}")
            if check.fallacy_type:
                lines.append(f"  - Fallacy Type: {check.fallacy_type}")
        lines.append("")
        lines.append(f"**Overall Assessment:** {r.fact_check.overall_assessment}")
        lines.append("")

        # Moderator
        lines.append("### ⚖️ Moderator's Ruling")
        lines.append("")
        lines.append(f"**Round Summary:** {r.moderator.round_summary}")
        lines.append("")
        if r.moderator.key_divergences:
            lines.append("**Key Divergences:**")
            lines.append("")
            for d in r.moderator.key_divergences:
                lines.append(f"- {d}")
            lines.append("")
        score = r.moderator.convergence_score
        bar_len = 20
        filled = int(score * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"**Convergence Score:** `{bar}` {score:.0%}")
        lines.append("")
        continue_text = "✅ Continue" if r.moderator.should_continue else "🛑 Terminate"
        lines.append(f"**Ruling:** {continue_text}")
        if r.moderator.guidance_for_next_round:
            lines.append("")
            lines.append(f"**Next Round Focus:** {r.moderator.guidance_for_next_round}")
        lines.append("")

    # Termination info
    lines.append("---")
    lines.append("")
    status_labels = {
        "converged": "✅ Converged",
        "max_rounds": "⏱️ Max Rounds Reached",
        "error": "❌ Error",
    }
    lines.append(f"**Debate Terminated:** {status_labels.get(state.status.value, state.status.value)}")
    if state.convergence_reason:
        lines.append(f"**Termination Reason:** {state.convergence_reason}")
    lines.append("")

    return lines


def render_report_to_markdown(report: DecisionReport, state: DebateState) -> str:
    """Render a DecisionReport to Markdown (includes full debate transcript + analysis summary)."""
    lines = []

    # Report header
    lines.append(f"# Decision Analysis Report")
    lines.append("")
    lines.append(f"**Decision Question:** {report.question}")
    lines.append("")

    # === Part 1: Full Debate Transcript ===
    lines.extend(_render_transcript(state))

    # === Part 2: Analysis ===
    lines.append("---")
    lines.append("")
    lines.append("# Part 2: Analysis Summary")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")

    # Recommendation
    lines.append("## Recommendation")
    lines.append("")
    confidence_map = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}
    confidence_label = confidence_map.get(report.recommendation.confidence.value, report.recommendation.confidence.value)
    lines.append(f"**Direction:** {report.recommendation.direction}")
    lines.append("")
    lines.append(f"**Confidence:** {confidence_label}")
    lines.append("")
    if report.recommendation.conditions:
        lines.append("**Preconditions:**")
        for cond in report.recommendation.conditions:
            lines.append(f"- {cond}")
        lines.append("")

    # Pro Arguments
    lines.append("## Pro Arguments (by strength)")
    lines.append("")
    if report.pro_arguments:
        for i, arg in enumerate(report.pro_arguments, 1):
            lines.append(f"### {i}. {arg.claim}")
            lines.append("")
            lines.append(f"- **Strength:** {arg.strength}/10")
            lines.append(f"- **Challenges Survived:** {arg.survived_challenges}")
            if arg.modifications:
                lines.append(f"- **Modification History:**")
                for mod in arg.modifications:
                    lines.append(f"  - {mod}")
            if arg.supporting_evidence:
                lines.append(f"- **Supporting Evidence:** {arg.supporting_evidence}")
            lines.append("")
    else:
        lines.append("*No surviving arguments*")
        lines.append("")

    # Con Arguments
    lines.append("## Con Arguments (by strength)")
    lines.append("")
    if report.con_arguments:
        for i, arg in enumerate(report.con_arguments, 1):
            lines.append(f"### {i}. {arg.claim}")
            lines.append("")
            lines.append(f"- **Strength:** {arg.strength}/10")
            lines.append(f"- **Challenges Survived:** {arg.survived_challenges}")
            if arg.modifications:
                lines.append(f"- **Modification History:**")
                for mod in arg.modifications:
                    lines.append(f"  - {mod}")
            if arg.supporting_evidence:
                lines.append(f"- **Supporting Evidence:** {arg.supporting_evidence}")
            lines.append("")
    else:
        lines.append("*No surviving arguments*")
        lines.append("")

    # Resolved Disagreements
    if report.resolved_disagreements:
        lines.append("## Resolved Disagreements")
        lines.append("")
        for item in report.resolved_disagreements:
            lines.append(f"- {item}")
        lines.append("")

    # Unresolved Disagreements
    if report.unresolved_disagreements:
        lines.append("## Unresolved Disagreements")
        lines.append("")
        for item in report.unresolved_disagreements:
            lines.append(f"- {item}")
        lines.append("")

    # Risk Factors
    if report.risk_factors:
        lines.append("## Risk Factors")
        lines.append("")
        for item in report.risk_factors:
            lines.append(f"- {item}")
        lines.append("")

    # Next Steps
    if report.next_steps:
        lines.append("## Next Steps")
        lines.append("")
        for i, step in enumerate(report.next_steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    # Debate Stats
    lines.append("## Debate Statistics")
    lines.append("")
    stats = report.debate_stats
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Rounds | {stats.total_rounds} |")
    lines.append(f"| Arguments Raised | {stats.arguments_raised} |")
    lines.append(f"| Arguments Survived | {stats.arguments_survived} |")
    lines.append(f"| Converged | {'Yes' if stats.convergence_achieved else 'No'} |")
    if stats.total_tokens:
        lines.append(f"| Token Usage | {stats.total_tokens:,} |")
    if stats.total_cost_usd:
        lines.append(f"| Estimated Cost | ${stats.total_cost_usd:.4f} |")
    lines.append("")

    return "\n".join(lines)
