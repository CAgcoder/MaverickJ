"""Interactive debate terminal — REPL entry point."""
import asyncio
import logging
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from maverickj.main import load_config, run_debate
from maverickj.output.renderer import render_report_to_markdown
from maverickj.schemas.report import DecisionReport

console = Console()


WELCOME = """
[bold cyan]Multi-Agent Debate Decision Engine — Interactive Mode[/bold cyan]

Four AI agents will conduct multi-round adversarial debate on your decision question:
  🟢 [green]Advocate[/green]      Builds the strongest pro arguments
  🔴 [red]Critic[/red]        Systematically challenges every argument
  🔍 [blue]Fact-Checker[/blue]  Neutral logic audit
  ⚖️  [yellow]Moderator[/yellow]    Controls pace and judges convergence

Enter a decision question to begin, or type [bold]quit[/bold] / [bold]exit[/bold] to leave.
"""


def _print_summary(state) -> None:
    """Print a brief summary after the debate concludes."""
    if not state or not state.final_report:
        return

    report = state.final_report
    if isinstance(report, dict):
        report = DecisionReport(**report)

    lines = []
    lines.append(f"[bold]Summary:[/bold] {report.executive_summary}")
    lines.append("")
    rec = report.recommendation
    confidence_colors = {"high": "green", "medium": "yellow", "low": "red"}
    c_color = confidence_colors.get(rec.confidence.value, "white")
    lines.append(f"[bold]Recommendation:[/bold] {rec.direction}")
    lines.append(f"[bold]Confidence:[/bold] [{c_color}]{rec.confidence.value.upper()}[/{c_color}]")
    if rec.conditions:
        lines.append(f"[bold]Preconditions:[/bold]")
        for cond in rec.conditions:
            lines.append(f"  • {cond}")

    console.print(Panel(
        "\n".join(lines),
        title="📊 Debate Conclusion",
        border_style="cyan",
        padding=(1, 2),
    ))


def _save_report(state) -> None:
    """Save the full report to a file."""
    if not state or not state.final_report:
        console.print("[yellow]No report available to save[/yellow]")
        return

    report = state.final_report
    if isinstance(report, dict):
        report = DecisionReport(**report)

    markdown = render_report_to_markdown(report, state)
    import os
    os.makedirs("reports", exist_ok=True)
    output_file = "reports/debate-report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    console.print(f"[green]📄 Report saved to: {output_file}[/green]")


def _build_followup_context(state) -> str:
    """Build context from the previous debate for use in a follow-up question."""
    if not state or not state.final_report:
        return ""

    report = state.final_report
    if isinstance(report, dict):
        report = DecisionReport(**report)

    lines = [
        f"[Previous Question] {state.question}",
        "",
        f"[Debate Conclusion] {report.executive_summary}",
        "",
        f"[Recommended Direction] {report.recommendation.direction}"
        f" (Confidence: {report.recommendation.confidence.value})",
    ]
    if report.recommendation.conditions:
        lines.append("[Preconditions] " + "; ".join(report.recommendation.conditions))
    if report.pro_arguments:
        lines += ["", "[Key Pro Arguments]"]
        for a in report.pro_arguments[:3]:
            lines.append(f"  - {a.claim} (strength {a.strength}/10)")
    if report.con_arguments:
        lines += ["", "[Key Con Arguments]"]
        for a in report.con_arguments[:3]:
            lines.append(f"  - {a.claim} (strength {a.strength}/10)")
    if report.unresolved_disagreements:
        lines += ["", "[Unresolved Disagreements]"]
        for d in report.unresolved_disagreements[:3]:
            lines.append(f"  - {d}")

    return "\n".join(lines)


def _sanitize(text: str) -> str:
    """Remove surrogate characters that can't be encoded as UTF-8 (macOS terminal / Docker TTY encoding issues)."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


async def _interactive_loop() -> None:
    """Interactive main loop."""
    config = load_config()

    while True:
        console.print()
        try:
            question = _sanitize(console.input("[bold cyan]📋 Enter your decision question:[/bold cyan] ").strip())
        except (EOFError, KeyboardInterrupt):
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break

        context = _sanitize(console.input("[dim]📎 Additional context (optional, press Enter to skip):[/dim] ").strip()) or None

        console.print()
        try:
            state = await run_debate(question, config, context)
        except KeyboardInterrupt:
            console.print("\n[yellow]Debate interrupted[/yellow]")
            continue
        except Exception as e:
            console.print(f"\n[red]Debate error: {e}[/red]")
            continue

        # Show brief summary
        _print_summary(state)

        # Post-debate menu
        while True:
            console.print("\n[bold]Next:[/bold]")
            console.print("  [cyan][1][/cyan] New topic")
            console.print("  [cyan][2][/cyan] Save full report")
            console.print("  [cyan][3][/cyan] Exit")
            console.print("  [cyan][4][/cyan] Follow-up (continue based on this debate)")

            try:
                choice = console.input("\n[bold]Choice:[/bold] ").strip()
            except (EOFError, KeyboardInterrupt):
                return

            if choice == "1":
                break
            elif choice == "2":
                _save_report(state)
            elif choice == "3":
                return
            elif choice == "4":
                try:
                    followup = console.input("[bold cyan]📋 Follow-up question:[/bold cyan] ").strip()
                except (EOFError, KeyboardInterrupt):
                    return
                if not followup:
                    continue
                followup_context = _build_followup_context(state)
                followup = _sanitize(followup)
                console.print()
                try:
                    state = await run_debate(followup, config, followup_context)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Debate interrupted[/yellow]")
                    continue
                except Exception as e:
                    console.print(f"\n[red]Debate error: {e}[/red]")
                    continue
                _print_summary(state)
            else:
                console.print("[dim]Please enter 1, 2, 3, or 4[/dim]")


def main():
    """Interactive CLI entry point."""
    load_dotenv()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )

    console.print(WELCOME)

    try:
        asyncio.run(_interactive_loop())
    except KeyboardInterrupt:
        pass

    console.print("\n[dim]Goodbye![/dim]\n")


if __name__ == "__main__":
    main()
