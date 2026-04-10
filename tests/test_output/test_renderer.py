"""Tests for report rendering."""
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
            question="Test question",
            executive_summary="This is a test summary.",
            recommendation=Recommendation(
                direction="Proceed",
                confidence=ConfidenceLevel.MEDIUM,
                conditions=["Condition 1", "Condition 2"],
            ),
            pro_arguments=[
                ScoredArgument(
                    claim="Pro argument 1",
                    strength=8,
                    survived_challenges=2,
                    modifications=["Revision 1"],
                ),
            ],
            con_arguments=[
                ScoredArgument(
                    claim="Con argument 1",
                    strength=6,
                    survived_challenges=1,
                ),
            ],
            resolved_disagreements=["Resolved 1"],
            unresolved_disagreements=["Unresolved 1"],
            risk_factors=["Risk 1"],
            next_steps=["Step 1"],
            debate_stats=DebateStats(
                total_rounds=3,
                arguments_raised=10,
                arguments_survived=6,
                convergence_achieved=True,
            ),
        )

        markdown = render_report_to_markdown(report, sample_debate_state)

        assert "# Decision Analysis Report" in markdown
        assert "Test question" in markdown
        assert "This is a test summary" in markdown
        assert "Proceed" in markdown
        assert "🟡 Medium" in markdown
        assert "Pro argument 1" in markdown
        assert "Con argument 1" in markdown
        assert "8/10" in markdown
        assert "Resolved 1" in markdown
        assert "Unresolved 1" in markdown
        assert "Risk 1" in markdown
        assert "Step 1" in markdown

    def test_render_empty_arguments(self, sample_debate_state):
        report = DecisionReport(
            question="Empty arguments test",
            executive_summary="No arguments",
            recommendation=Recommendation(
                direction="Cannot determine",
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
        assert "*No surviving arguments*" in markdown
