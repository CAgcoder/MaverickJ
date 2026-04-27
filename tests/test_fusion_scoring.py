"""Deterministic tests for supply-chain fusion scoring (no LLM)."""

import uuid
from datetime import datetime

from maverickj.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse
from maverickj.schemas.arguments import (
    Argument,
    ArgumentRecord,
    ArgumentStatus,
    FactCheck,
    FactCheckVerdict,
)
from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateRound, DebateState, DebateStatus
from maverickj.schemas.supply_chain_engine import SupplyChainConfig
from maverickj.supply_chain.fusion_scoring import (
    collect_scored_arguments,
    filter_high_score_arguments,
)


def _state_with_scores(
    *,
    factuality: float,
    logic: float,
    feasibility: float,
    relevance: float,
) -> DebateState:
    arg = Argument(id="A-1", claim="c1", reasoning="r1", status=ArgumentStatus.ACTIVE)
    fc = FactCheckResponse(
        checks=[
            FactCheck(
                target_argument_id="A-1",
                verdict=FactCheckVerdict.VALID,
                explanation="e",
                factuality_score=factuality,
                logic_score=logic,
            )
        ],
        overall_assessment="",
    )
    mod = ModeratorResponse(
        round_summary="x",
        key_divergences=[],
        convergence_score=0.5,
        should_continue=True,
        feasibility_scores={"A-1": feasibility},
        relevance_scores={"A-1": relevance},
    )
    rnd = DebateRound(
        round_number=1,
        advocate=AgentResponse(agent_role="advocate", arguments=[arg]),
        critic=AgentResponse(agent_role="critic", arguments=[]),
        fact_check=fc,
        moderator=mod,
    )
    return DebateState(
        id=str(uuid.uuid4()),
        question="q",
        config=DebateConfig(),
        rounds=[rnd],
        argument_registry={
            "A-1": ArgumentRecord(argument=arg, raised_in_round=1, raised_by="advocate"),
        },
        current_round=1,
        status=DebateStatus.RUNNING,
        metadata=DebateMetadata(started_at=datetime.now()),
    )


def test_composite_is_mean_of_four_dims():
    s = _state_with_scores(factuality=8.0, logic=8.0, feasibility=8.0, relevance=8.0)
    rows = collect_scored_arguments(s)
    assert len(rows) == 1
    assert abs(rows[0].composite - 8.0) < 1e-6


def test_filter_respects_thresholds():
    sc = SupplyChainConfig()
    # composite 8.0, factuality 8.0 -> passes default 8.0 / 7.0
    s = _state_with_scores(factuality=8.0, logic=8.0, feasibility=8.0, relevance=8.0)
    scored = collect_scored_arguments(s)
    assert len(filter_high_score_arguments(scored, sc)) == 1

    # Lower factuality below 7.0 -> filtered out
    s2 = _state_with_scores(factuality=6.0, logic=10.0, feasibility=10.0, relevance=10.0)
    scored2 = collect_scored_arguments(s2)
    assert len(filter_high_score_arguments(scored2, sc)) == 0
