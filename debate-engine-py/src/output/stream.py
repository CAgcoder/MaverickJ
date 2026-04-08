"""实时辩论过程的控制台输出 — rich 增强版"""
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from src.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse

console = Console()

# 角色配色
AGENT_STYLES = {
    "advocate": {"color": "green", "icon": "🟢", "label": "正方论证者"},
    "critic": {"color": "red", "icon": "🔴", "label": "反方批评者"},
    "fact_checker": {"color": "blue", "icon": "🔍", "label": "事实校验者"},
    "moderator": {"color": "yellow", "icon": "⚖️ ", "label": "主持人"},
}


def print_debate_start(question: str) -> None:
    console.print()
    console.print(Rule("[bold cyan]🎯 多 Agent 辩论式决策引擎[/bold cyan]", style="cyan"))
    console.print(f"\n[bold]📋 决策问题:[/bold] {question}\n")


def print_round_start(round_number: int) -> None:
    console.print()
    console.print(Rule(f"[bold]📍 第 {round_number} 轮辩论[/bold]", style="dim"))


def print_agent_start(agent: str) -> None:
    style = AGENT_STYLES.get(agent, {})
    icon = style.get("icon", "")
    label = style.get("label", agent)
    color = style.get("color", "white")
    console.print(f"\n  [{color}]{icon} {label} 思考中...[/{color}]")


def _format_agent_result(result: AgentResponse, role: str) -> str:
    """格式化 Advocate/Critic 的完整输出"""
    lines = []

    # 论点
    for arg in result.arguments:
        status_icon = "✅" if arg.status.value == "active" else "🔄"
        lines.append(f"{status_icon} [bold][{arg.id}] {arg.claim}[/bold]")
        lines.append(f"   [dim]推理:[/dim] {arg.reasoning}")
        if arg.evidence:
            lines.append(f"   [dim]证据:[/dim] {arg.evidence}")
        lines.append("")

    # 反驳
    if result.rebuttals:
        lines.append("[bold]反驳:[/bold]")
        for r in result.rebuttals:
            lines.append(f"  ↳ 针对 [bold]{r.target_argument_id}[/bold]: {r.counter_claim}")
            lines.append(f"    [dim]推理:[/dim] {r.reasoning}")
        lines.append("")

    # 让步
    if result.concessions:
        lines.append("[bold]让步:[/bold]")
        for c in result.concessions:
            lines.append(f"  🤝 {c}")
        lines.append("")

    # 信心变化
    shift = result.confidence_shift
    shift_color = "green" if shift > 0 else "red" if shift < 0 else "dim"
    lines.append(f"[{shift_color}]信心变化: {shift:+.2f}[/{shift_color}]")

    return "\n".join(lines)


def print_advocate_result(result: AgentResponse) -> None:
    content = _format_agent_result(result, "advocate")
    console.print(Panel(
        content,
        title="🟢 正方论证者",
        border_style="green",
        padding=(1, 2),
    ))


def print_critic_result(result: AgentResponse) -> None:
    content = _format_agent_result(result, "critic")
    console.print(Panel(
        content,
        title="🔴 反方批评者",
        border_style="red",
        padding=(1, 2),
    ))


def print_fact_check_result(result: FactCheckResponse) -> None:
    verdict_styles = {
        "valid": ("✅", "green"),
        "flawed": ("❌", "red"),
        "needs_context": ("⚠️ ", "yellow"),
        "unverifiable": ("❓", "dim"),
    }

    lines = []
    for check in result.checks:
        icon, color = verdict_styles.get(check.verdict.value, ("•", "white"))
        lines.append(f"{icon} [bold][{check.target_argument_id}][/bold] [{color}]{check.verdict.value}[/{color}]")
        lines.append(f"   {check.explanation}")
        if check.correction:
            lines.append(f"   [yellow]修正建议:[/yellow] {check.correction}")
        if check.fallacy_type:
            lines.append(f"   [red]谬误类型:[/red] {check.fallacy_type}")
        lines.append("")

    lines.append(f"[bold]整体评估:[/bold] {result.overall_assessment}")

    console.print(Panel(
        "\n".join(lines),
        title="🔍 事实校验者",
        border_style="blue",
        padding=(1, 2),
    ))


def print_moderator_result(result: ModeratorResponse) -> None:
    lines = []

    # 轮次总结
    lines.append(f"[bold]本轮总结:[/bold]\n{result.round_summary}")
    lines.append("")

    # 关键分歧
    if result.key_divergences:
        lines.append("[bold]关键分歧:[/bold]")
        for d in result.key_divergences:
            lines.append(f"  • {d}")
        lines.append("")

    # 收敛分数 — 可视化进度条
    score = result.convergence_score
    bar_len = 20
    filled = int(score * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
    lines.append(f"[bold]收敛分数:[/bold] [{score_color}]{bar} {score:.0%}[/{score_color}]")

    # 是否继续
    continue_text = "[green]继续辩论[/green]" if result.should_continue else "[red]终止辩论[/red]"
    lines.append(f"[bold]裁决:[/bold] {continue_text}")

    # 下轮引导
    if result.guidance_for_next_round:
        lines.append(f"\n[bold]下轮焦点:[/bold]\n{result.guidance_for_next_round}")

    console.print(Panel(
        "\n".join(lines),
        title="⚖️  主持人",
        border_style="yellow",
        padding=(1, 2),
    ))


def print_debate_complete(status: str, reason: Optional[str] = None) -> None:
    status_labels = {
        "converged": "[green]✅ 辩论收敛[/green]",
        "max_rounds": "[yellow]⏱️  达到最大轮数[/yellow]",
        "error": "[red]❌ 辩论出错[/red]",
    }
    label = status_labels.get(status, status)

    lines = [f"[bold]辩论结束:[/bold] {label}"]
    if reason:
        lines.append(f"[dim]原因: {reason}[/dim]")

    console.print()
    console.print(Rule(style="cyan"))
    console.print("\n".join(lines))
    console.print(Rule(style="cyan"))
