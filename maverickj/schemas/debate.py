from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field

from maverickj.schemas.agents import AgentResponse, FactCheckResponse, ModeratorResponse
from maverickj.schemas.arguments import ArgumentRecord


class DebateStatus(str, Enum):
    RUNNING = "running"
    CONVERGED = "converged"
    MAX_ROUNDS = "max_rounds"
    ERROR = "error"


class DebateConfig(BaseModel):
    max_rounds: int = 5
    convergence_threshold: int = 2
    convergence_score_target: float = 0.8
    language: str = "auto"
    transcript_compression_after_round: int = 2


class DebateMetadata(BaseModel):
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_llm_calls: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0


class DebateRound(BaseModel):
    round_number: int
    advocate: AgentResponse
    critic: AgentResponse
    fact_check: FactCheckResponse
    moderator: ModeratorResponse


class DebateState(BaseModel):
    """Shared state object passed between all LangGraph nodes."""
    id: str
    question: str
    context: Optional[str] = None
    config: DebateConfig
    rounds: list[DebateRound] = []
    argument_registry: dict[str, ArgumentRecord] = {}
    current_round: int = 0
    status: DebateStatus = DebateStatus.RUNNING
    convergence_reason: Optional[str] = None
    final_report: Optional[Any] = None  # DecisionReport, use Any to avoid circular import
    metadata: DebateMetadata
    # Transient fields for current round in-progress data
    current_round_advocate: Optional[AgentResponse] = None
    current_round_critic: Optional[AgentResponse] = None
    current_round_fact_check: Optional[FactCheckResponse] = None
    current_round_moderator: Optional[ModeratorResponse] = None
