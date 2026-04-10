"""pytest fixtures"""
import pytest
from datetime import datetime

from maverickj.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse
from maverickj.schemas.arguments import Argument, ArgumentStatus, FactCheck, FactCheckVerdict, Rebuttal
from maverickj.schemas.config import DebateEngineConfig
from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateRound, DebateState, DebateStatus


@pytest.fixture
def debate_config():
    return DebateConfig(
        max_rounds=5,
        convergence_threshold=2,
        convergence_score_target=0.8,
        language="zh",
        transcript_compression_after_round=2,
    )


@pytest.fixture
def engine_config():
    return DebateEngineConfig(
        default_provider="claude",
        default_model="claude-sonnet-4-20250514",
        default_temperature=0.7,
    )


@pytest.fixture
def sample_advocate_response():
    return AgentResponse(
        agent_role="advocate",
        arguments=[
            Argument(
                id="ADV-R1-01",
                claim="Go binaries are small; deployment costs drop significantly",
                reasoning="Compared to the ~200-500 MB JVM runtime, a Go service typically needs only 20-50 MB",
                evidence="Multiple companies report 60-80% reduction in container resources after migration",
                status=ArgumentStatus.ACTIVE,
            ),
            Argument(
                id="ADV-R1-02",
                claim="Go cold-start time far outperforms Java",
                reasoning="Go compiles to native binary; startup time is in milliseconds",
                status=ArgumentStatus.ACTIVE,
            ),
        ],
        rebuttals=[],
        concessions=[],
        confidence_shift=0.0,
    )


@pytest.fixture
def sample_critic_response():
    return AgentResponse(
        agent_role="critic",
        arguments=[
            Argument(
                id="CRT-R1-01",
                claim="Migration cost is extremely high; a large codebase must be rewritten",
                reasoning="Three years of Java code cannot be automatically converted to Go",
                status=ArgumentStatus.ACTIVE,
            ),
        ],
        rebuttals=[
            Rebuttal(
                target_argument_id="ADV-R1-01",
                counter_claim="Deployment-cost savings are offset by dual-system maintenance during migration",
                reasoning="During migration both the Java and Go systems must be maintained simultaneously",
            ),
        ],
        concessions=[],
        confidence_shift=0.0,
    )


@pytest.fixture
def sample_fact_check_response():
    return FactCheckResponse(
        checks=[
            FactCheck(
                target_argument_id="ADV-R1-01",
                verdict=FactCheckVerdict.VALID,
                explanation="Go's memory-footprint advantage is well-supported by real-world case studies",
            ),
            FactCheck(
                target_argument_id="CRT-R1-01",
                verdict=FactCheckVerdict.VALID,
                explanation="Large-scale code migration costs are a well-known risk",
            ),
        ],
        overall_assessment="Both sides' arguments are internally consistent",
    )


@pytest.fixture
def sample_moderator_response():
    return ModeratorResponse(
        round_summary="Round 1: Advocate focused on performance gains; Critic focused on migration costs",
        key_divergences=["Whether migration costs justify the performance gains", "Team's capacity to transition"],
        convergence_score=0.3,
        should_continue=True,
        guidance_for_next_round="Please focus on concrete cost estimates for the migration",
    )


@pytest.fixture
def sample_debate_round(
    sample_advocate_response,
    sample_critic_response,
    sample_fact_check_response,
    sample_moderator_response,
):
    return DebateRound(
        round_number=1,
        advocate=sample_advocate_response,
        critic=sample_critic_response,
        fact_check=sample_fact_check_response,
        moderator=sample_moderator_response,
    )


@pytest.fixture
def sample_debate_state(debate_config, sample_debate_round):
    return DebateState(
        id="test-debate-001",
        question="Should we migrate our Java backend to Go?",
        context="50-person team, 3 years on Spring Boot",
        config=debate_config,
        rounds=[sample_debate_round],
        argument_registry={},
        current_round=1,
        status=DebateStatus.RUNNING,
        metadata=DebateMetadata(started_at=datetime.now()),
    )
