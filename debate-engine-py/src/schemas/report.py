from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScoredArgument(BaseModel):
    claim: str = Field(description="论点主张")
    strength: int = Field(description="论点强度 1-10")
    survived_challenges: int = Field(description="经历挑战次数")
    modifications: list[str] = Field(default_factory=list, description="修正历史")
    supporting_evidence: Optional[str] = Field(default=None, description="支撑证据")


class Recommendation(BaseModel):
    direction: str = Field(description="建议方向")
    confidence: ConfidenceLevel = Field(description="置信度")
    conditions: list[str] = Field(description="建议成立的前提条件")


class DebateStats(BaseModel):
    total_rounds: int
    arguments_raised: int
    arguments_survived: int
    convergence_achieved: bool
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class DecisionReport(BaseModel):
    question: str
    executive_summary: str = Field(description="3-5 句话概括")
    recommendation: Recommendation
    pro_arguments: list[ScoredArgument] = Field(description="正方论点，按 strength 降序")
    con_arguments: list[ScoredArgument] = Field(description="反方论点，按 strength 降序")
    resolved_disagreements: list[str] = Field(default_factory=list)
    unresolved_disagreements: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    debate_stats: DebateStats
