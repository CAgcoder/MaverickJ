from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScoredArgument(BaseModel):
    claim: str = Field(description="Argument claim")
    strength: int = Field(description="Argument strength 1-10")
    survived_challenges: int = Field(description="Number of challenges survived")
    modifications: list[str] = Field(default_factory=list, description="Modification history")
    supporting_evidence: Optional[str] = Field(default=None, description="Supporting evidence")


class Recommendation(BaseModel):
    direction: str = Field(description="Recommended direction")
    confidence: ConfidenceLevel = Field(description="Confidence level")
    conditions: list[str] = Field(description="Preconditions for the recommendation to hold")


class DebateStats(BaseModel):
    total_rounds: int
    arguments_raised: int
    arguments_survived: int
    convergence_achieved: bool
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class DecisionReport(BaseModel):
    question: str
    executive_summary: str = Field(description="3-5 sentence summary")
    recommendation: Recommendation
    pro_arguments: list[ScoredArgument] = Field(description="Pro-side arguments sorted by strength descending")
    con_arguments: list[ScoredArgument] = Field(description="Con-side arguments sorted by strength descending")
    resolved_disagreements: list[str] = Field(default_factory=list)
    unresolved_disagreements: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    debate_stats: DebateStats
