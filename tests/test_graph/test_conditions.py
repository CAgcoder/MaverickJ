"""Tests for convergence conditions."""
from datetime import datetime

import pytest

from maverickj.graph.conditions import should_continue
from maverickj.schemas.agents import ModeratorResponse
from maverickj.schemas.debate import (
    DebateConfig,
    DebateMetadata,
    DebateRound,
    DebateState,
    DebateStatus,
)


def _make_state(
    rounds=None,
    current_round=1,
    max_rounds=5,
    status=DebateStatus.RUNNING,
) -> DebateState:
    return DebateState(
        id="test",
        question="test",
        config=DebateConfig(max_rounds=max_rounds, convergence_score_target=0.8),
        rounds=rounds or [],
        current_round=current_round,
        status=status,
        metadata=DebateMetadata(started_at=datetime.now()),
    )


def _make_round(round_num: int, should_cont: bool, score: float) -> DebateRound:
    from maverickj.schemas.agents import AgentResponse, FactCheckResponse
    from maverickj.schemas.arguments import Argument

    dummy_agent = AgentResponse(
        agent_role="advocate",
        arguments=[Argument(id=f"X-R{round_num}-01", claim="test", reasoning="test")],
    )
    dummy_fc = FactCheckResponse(checks=[], overall_assessment="ok")
    mod = ModeratorResponse(
        round_summary="summary",
        key_divergences=[],
        convergence_score=score,
        should_continue=should_cont,
    )
    return DebateRound(
        round_number=round_num,
        advocate=dummy_agent,
        critic=dummy_agent,
        fact_check=dummy_fc,
        moderator=mod,
    )


class TestShouldContinue:
    def test_max_rounds_reached(self):
        state = _make_state(current_round=5, max_rounds=5)
        assert should_continue(state) == "terminate"

    def test_error_state(self):
        state = _make_state(status=DebateStatus.ERROR)
        assert should_continue(state) == "terminate"

    def test_moderator_says_stop(self):
        r1 = _make_round(1, should_cont=False, score=0.9)
        state = _make_state(rounds=[r1], current_round=1)
        assert should_continue(state) == "terminate"

    def test_moderator_says_continue(self):
        r1 = _make_round(1, should_cont=True, score=0.3)
        state = _make_state(rounds=[r1], current_round=1)
        assert should_continue(state) == "continue"

    def test_double_high_convergence(self):
        r1 = _make_round(1, should_cont=True, score=0.85)
        r2 = _make_round(2, should_cont=True, score=0.82)
        state = _make_state(rounds=[r1, r2], current_round=2)
        assert should_continue(state) == "terminate"

    def test_no_rounds_yet(self):
        state = _make_state(rounds=[], current_round=0)
        assert should_continue(state) == "continue"
