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
                claim="Go 语言编译后二进制体积小，部署成本显著降低",
                reasoning="相比 JVM 约 200-500MB 的运行时内存，Go 服务通常只需 20-50MB",
                evidence="多家公司迁移后报告容器资源降低 60-80%",
                status=ArgumentStatus.ACTIVE,
            ),
            Argument(
                id="ADV-R1-02",
                claim="Go 冷启动速度远超 Java",
                reasoning="Go 编译为原生二进制，启动时间在毫秒级",
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
                claim="迁移成本极高，需要重写大量业务代码",
                reasoning="3 年积累的 Java 代码无法自动转换为 Go",
                status=ArgumentStatus.ACTIVE,
            ),
        ],
        rebuttals=[
            Rebuttal(
                target_argument_id="ADV-R1-01",
                counter_claim="部署成本降低被迁移期间的双系统维护成本抵消",
                reasoning="迁移期间需要同时维护 Java 和 Go 两套系统",
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
                explanation="Go 的内存占用优势有大量实际案例支撑",
            ),
            FactCheck(
                target_argument_id="CRT-R1-01",
                verdict=FactCheckVerdict.VALID,
                explanation="大规模代码迁移成本确实是已知风险",
            ),
        ],
        overall_assessment="双方论点整体逻辑自洽",
    )


@pytest.fixture
def sample_moderator_response():
    return ModeratorResponse(
        round_summary="第一轮正方聚焦性能优势，反方聚焦迁移成本",
        key_divergences=["迁移成本是否值得性能收益", "团队转型能力"],
        convergence_score=0.3,
        should_continue=True,
        guidance_for_next_round="请聚焦讨论迁移的具体成本估算",
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
        question="我们应该将 Java 后端迁移到 Go 吗？",
        context="50 人团队，Spring Boot 3 年",
        config=debate_config,
        rounds=[sample_debate_round],
        argument_registry={},
        current_round=1,
        status=DebateStatus.RUNNING,
        metadata=DebateMetadata(started_at=datetime.now()),
    )
