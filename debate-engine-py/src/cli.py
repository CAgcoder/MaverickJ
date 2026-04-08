"""交互式辩论终端 — REPL 入口"""
import asyncio
import logging
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from src.main import load_config, run_debate
from src.output.renderer import render_report_to_markdown
from src.schemas.report import DecisionReport

console = Console()


WELCOME = """
[bold cyan]多 Agent 辩论式决策引擎 — 交互模式[/bold cyan]

四个 AI Agent 将围绕你的决策问题展开多轮对抗式辩论：
  🟢 [green]正方论证者[/green]  构建最强正面论据
  🔴 [red]反方批评者[/red]  系统性挑战每个论点
  🔍 [blue]事实校验者[/blue]  中立逻辑审计
  ⚖️  [yellow]主持人[/yellow]      控制节奏，判断收敛

输入决策问题即可开始，输入 [bold]quit[/bold] 或 [bold]exit[/bold] 退出。
"""


def _print_summary(state) -> None:
    """辩论结束后打印简要结论"""
    if not state or not state.final_report:
        return

    report = state.final_report
    if isinstance(report, dict):
        report = DecisionReport(**report)

    lines = []
    lines.append(f"[bold]概要:[/bold] {report.executive_summary}")
    lines.append("")
    rec = report.recommendation
    confidence_colors = {"high": "green", "medium": "yellow", "low": "red"}
    c_color = confidence_colors.get(rec.confidence.value, "white")
    lines.append(f"[bold]建议:[/bold] {rec.direction}")
    lines.append(f"[bold]置信度:[/bold] [{c_color}]{rec.confidence.value.upper()}[/{c_color}]")
    if rec.conditions:
        lines.append(f"[bold]前提条件:[/bold]")
        for cond in rec.conditions:
            lines.append(f"  • {cond}")

    console.print(Panel(
        "\n".join(lines),
        title="📊 辩论结论",
        border_style="cyan",
        padding=(1, 2),
    ))


def _save_report(state) -> None:
    """保存完整报告到文件"""
    if not state or not state.final_report:
        console.print("[yellow]没有可保存的报告[/yellow]")
        return

    report = state.final_report
    if isinstance(report, dict):
        report = DecisionReport(**report)

    markdown = render_report_to_markdown(report, state)
    output_file = "debate-report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    console.print(f"[green]📄 报告已保存至: {output_file}[/green]")


async def _interactive_loop() -> None:
    """交互式主循环"""
    config = load_config()

    while True:
        console.print()
        try:
            question = console.input("[bold cyan]📋 请输入决策问题:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break

        context = console.input("[dim]📎 补充背景（可选，按回车跳过）:[/dim] ").strip() or None

        console.print()
        try:
            state = await run_debate(question, config, context)
        except KeyboardInterrupt:
            console.print("\n[yellow]辩论已中断[/yellow]")
            continue
        except Exception as e:
            console.print(f"\n[red]辩论出错: {e}[/red]")
            continue

        # 显示简要结论
        _print_summary(state)

        # 辩论后菜单
        while True:
            console.print("\n[bold]下一步:[/bold]")
            console.print("  [cyan][1][/cyan] 新话题")
            console.print("  [cyan][2][/cyan] 保存完整报告")
            console.print("  [cyan][3][/cyan] 退出")

            try:
                choice = console.input("\n[bold]选择:[/bold] ").strip()
            except (EOFError, KeyboardInterrupt):
                return

            if choice == "1":
                break
            elif choice == "2":
                _save_report(state)
            elif choice == "3":
                return
            else:
                console.print("[dim]请输入 1、2 或 3[/dim]")


def main():
    """交互式 CLI 入口"""
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

    console.print("\n[dim]再见！[/dim]\n")


if __name__ == "__main__":
    main()
