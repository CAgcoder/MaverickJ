"""Real-time debate console output — Rich-enhanced."""
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from maverickj.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse

console = Console()

# Agent role styles
AGENT_STYLES = {
    "advocate": {"color": "green", "icon": "🟢", "label": "Advocate"},
    "critic": {"color": "red", "icon": "🔴", "label": "Critic"},
    "fact_checker": {"color": "blue", "icon": "🔍", "label": "Fact-Checker"},
    "moderator": {"color": "yellow", "icon": "⚖️ ", "label": "Moderator"},
}


def print_debate_start(question: str) -> None:
    console.print()
    console.print(Rule("[bold cyan]🎯 Multi-Agent Debate Decision Engine[/bold cyan]", style="cyan"))
    console.print(f"\n[bold]📋 Decision Question:[/bold] {question}\n")


def print_round_start(round_number: int) -> None:
    console.print()
    console.print(Rule(f"[bold]📍 Round {round_number}[/bold]", style="dim"))


def print_agent_start(agent: str) -> None:
    style = AGENT_STYLES.get(agent, {})
    icon = style.get("icon", "")
    label = style.get("label", agent)
    color = style.get("color", "white")
    console.print(f"\n  [{color}]{icon} {label} thinking...[/{color}]")


def _format_agent_result(result: AgentResponse, role: str) -> str:
    """Format the full output of an Advocate or Critic response."""
    lines = []

    # Arguments
    for arg in result.arguments:
        status_icon = "✅" if arg.status.value == "active" else "🔄"
        lines.append(f"{status_icon} [bold][{arg.id}] {arg.claim}[/bold]")
        lines.append(f"   [dim]Reasoning:[/dim] {arg.reasoning}")
        if arg.evidence:
            lines.append(f"   [dim]Evidence:[/dim] {arg.evidence}")
        lines.append("")

    # Rebuttals
    if result.rebuttals:
        lines.append("[bold]Rebuttals:[/bold]")
        for r in result.rebuttals:
            lines.append(f"  ↳ Against [bold]{r.target_argument_id}[/bold]: {r.counter_claim}")
            lines.append(f"    [dim]Reasoning:[/dim] {r.reasoning}")
        lines.append("")

    # Concessions
    if result.concessions:
        lines.append("[bold]Concessions:[/bold]")
        for c in result.concessions:
            lines.append(f"  🤝 {c}")
        lines.append("")

    # Confidence shift
    shift = result.confidence_shift
    shift_color = "green" if shift > 0 else "red" if shift < 0 else "dim"
    lines.append(f"[{shift_color}]Confidence Shift: {shift:+.2f}[/{shift_color}]")

    return "\n".join(lines)


def print_advocate_result(result: AgentResponse) -> None:
    content = _format_agent_result(result, "advocate")
    console.print(Panel(
        content,
        title="🟢 Advocate",
        border_style="green",
        padding=(1, 2),
    ))


def print_critic_result(result: AgentResponse) -> None:
    content = _format_agent_result(result, "critic")
    console.print(Panel(
        content,
        title="🔴 Critic",
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
            lines.append(f"   [yellow]Correction:[/yellow] {check.correction}")
        if check.fallacy_type:
            lines.append(f"   [red]Fallacy Type:[/red] {check.fallacy_type}")
        lines.append("")

    lines.append(f"[bold]Overall Assessment:[/bold] {result.overall_assessment}")

    console.print(Panel(
        "\n".join(lines),
        title="🔍 Fact-Checker",
        border_style="blue",
        padding=(1, 2),
    ))


def print_moderator_result(result: ModeratorResponse) -> None:
    lines = []

    # Round summary
    lines.append(f"[bold]Round Summary:[/bold]\n{result.round_summary}")
    lines.append("")

    # Key divergences
    if result.key_divergences:
        lines.append("[bold]Key Divergences:[/bold]")
        for d in result.key_divergences:
            lines.append(f"  • {d}")
        lines.append("")

    # Convergence score visualised as a progress bar
    score = result.convergence_score
    bar_len = 20
    filled = int(score * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
    lines.append(f"[bold]Convergence Score:[/bold] [{score_color}]{bar} {score:.0%}[/{score_color}]")

    # Continue or terminate
    continue_text = "[green]Continue[/green]" if result.should_continue else "[red]Terminate[/red]"
    lines.append(f"[bold]Ruling:[/bold] {continue_text}")

    # Next round guidance
    if result.guidance_for_next_round:
        lines.append(f"\n[bold]Next Round Focus:[/bold]\n{result.guidance_for_next_round}")

    console.print(Panel(
        "\n".join(lines),
        title="⚖️  Moderator",
        border_style="yellow",
        padding=(1, 2),
    ))


def print_debate_complete(status: str, reason: Optional[str] = None) -> None:
    status_labels = {
        "converged": "[green]✅ Converged[/green]",
        "max_rounds": "[yellow]⏱️  Max Rounds Reached[/yellow]",
        "error": "[red]❌ Error[/red]",
    }
    label = status_labels.get(status, status)

    lines = [f"[bold]Debate Complete:[/bold] {label}"]
    if reason:
        lines.append(f"[dim]Reason: {reason}[/dim]")

    console.print()
    console.print(Rule(style="cyan"))
    console.print("\n".join(lines))
    console.print(Rule(style="cyan"))
