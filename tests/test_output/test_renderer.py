"""测试报告渲染"""
import pytest

from maverickj.output.renderer import render_report_to_markdown
from maverickj.schemas.report import (
    ConfidenceLevel,
    DebateStats,
    DecisionReport,
    Recommendation,
    ScoredArgument,
)


class TestReportRenderer:
    def test_render_basic_report(self, sample_debate_state):
        report = DecisionReport(
            question="测试问题",
            executive_summary="这是一个测试摘要。",
            recommendation=Recommendation(
                direction="建议执行",
                confidence=ConfidenceLevel.MEDIUM,
                conditions=["条件一", "条件二"],
            ),
            pro_arguments=[
                ScoredArgument(
                    claim="正方论点1",
                    strength=8,
                    survived_challenges=2,
                    modifications=["修正1"],
                ),
            ],
            con_arguments=[
                ScoredArgument(
                    claim="反方论点1",
                    strength=6,
                    survived_challenges=1,
                ),
            ],
            resolved_disagreements=["已解决1"],
            unresolved_disagreements=["未解决1"],
            risk_factors=["风险1"],
            next_steps=["步骤1"],
            debate_stats=DebateStats(
                total_rounds=3,
                arguments_raised=10,
                arguments_survived=6,
                convergence_achieved=True,
            ),
        )

        markdown = render_report_to_markdown(report, sample_debate_state)

        assert "# 决策分析报告" in markdown
        assert "测试问题" in markdown
        assert "这是一个测试摘要" in markdown
        assert "建议执行" in markdown
        assert "🟡 中" in markdown
        assert "正方论点1" in markdown
        assert "反方论点1" in markdown
        assert "8/10" in markdown
        assert "已解决1" in markdown
        assert "未解决1" in markdown
        assert "风险1" in markdown
        assert "步骤1" in markdown

    def test_render_empty_arguments(self, sample_debate_state):
        report = DecisionReport(
            question="空论点测试",
            executive_summary="无论点",
            recommendation=Recommendation(
                direction="无法判断",
                confidence=ConfidenceLevel.LOW,
                conditions=[],
            ),
            pro_arguments=[],
            con_arguments=[],
            debate_stats=DebateStats(
                total_rounds=1,
                arguments_raised=0,
                arguments_survived=0,
                convergence_achieved=False,
            ),
        )

        markdown = render_report_to_markdown(report, sample_debate_state)
        assert "*无存活论点*" in markdown
