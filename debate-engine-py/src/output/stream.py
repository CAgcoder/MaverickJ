"""实时辩论过程的控制台输出"""
import sys
from typing import Optional

from src.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse
from src.schemas.debate import DebateState


def print_debate_start(question: str) -> None:
    print("\n" + "=" * 60)
    print("🎯 多 Agent 辩论式决策引擎")
    print("=" * 60)
    print(f"\n📋 决策问题: {question}\n")


def print_round_start(round_number: int) -> None:
    print(f"\n{'─' * 50}")
    print(f"📍 第 {round_number} 轮辩论")
    print(f"{'─' * 50}")


def print_agent_start(agent: str) -> None:
    icons = {
        "advocate": "🟢 正方论证者",
        "critic": "🔴 反方批评者",
        "fact_checker": "🔍 事实校验者",
        "moderator": "⚖️  主持人",
    }
    label = icons.get(agent, agent)
    print(f"\n  {label} 发言中...")


def print_advocate_result(result: AgentResponse) -> None:
    print(f"  🟢 正方论证完成:")
    for arg in result.arguments:
        status_icon = "✅" if arg.status.value == "active" else "🔄"
        print(f"    {status_icon} [{arg.id}] {arg.claim}")
    if result.rebuttals:
        print(f"    反驳: {len(result.rebuttals)} 条")
    if result.concessions:
        print(f"    让步: {len(result.concessions)} 项")
    print(f"    信心变化: {result.confidence_shift:+.2f}")


def print_critic_result(result: AgentResponse) -> None:
    print(f"  🔴 反方论证完成:")
    for arg in result.arguments:
        status_icon = "✅" if arg.status.value == "active" else "🔄"
        print(f"    {status_icon} [{arg.id}] {arg.claim}")
    if result.rebuttals:
        print(f"    反驳: {len(result.rebuttals)} 条")
    if result.concessions:
        print(f"    让步: {len(result.concessions)} 项")
    print(f"    信心变化: {result.confidence_shift:+.2f}")


def print_fact_check_result(result: FactCheckResponse) -> None:
    print(f"  🔍 事实校验完成:")
    verdict_icons = {
        "valid": "✅",
        "flawed": "❌",
        "needs_context": "⚠️",
        "unverifiable": "❓",
    }
    for check in result.checks:
        icon = verdict_icons.get(check.verdict.value, "•")
        print(f"    {icon} [{check.target_argument_id}] {check.verdict.value}: {check.explanation[:80]}")


def print_moderator_result(result: ModeratorResponse) -> None:
    print(f"  ⚖️  主持人裁决:")
    print(f"    总结: {result.round_summary[:100]}...")
    print(f"    关键分歧: {len(result.key_divergences)} 项")
    print(f"    收敛分数: {result.convergence_score:.2f}")
    print(f"    是否继续: {'是' if result.should_continue else '否'}")
    if result.guidance_for_next_round:
        print(f"    下轮引导: {result.guidance_for_next_round[:80]}...")


def print_debate_complete(status: str, reason: Optional[str] = None) -> None:
    print(f"\n{'=' * 50}")
    status_labels = {
        "converged": "✅ 辩论收敛",
        "max_rounds": "⏱️  达到最大轮数",
        "error": "❌ 辩论出错",
    }
    label = status_labels.get(status, status)
    print(f"辩论结束: {label}")
    if reason:
        print(f"原因: {reason}")
    print(f"{'=' * 50}")
