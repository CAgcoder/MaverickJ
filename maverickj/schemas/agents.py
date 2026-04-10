from typing import Optional

from pydantic import BaseModel, Field

from maverickj.schemas.arguments import Argument, FactCheck, FactCheckVerdict, Rebuttal


class AgentResponse(BaseModel):
    """Common output format for Advocate and Critic agents."""
    agent_role: str = Field(description="Agent role: advocate or critic")
    arguments: list[Argument] = Field(description="Arguments raised this round")
    rebuttals: list[Rebuttal] = Field(default_factory=list, description="Rebuttals against the opponent's arguments")
    concessions: list[str] = Field(default_factory=list, description="Points conceded to the opponent")
    confidence_shift: float = Field(default=0.0, description="Confidence change this round [-1, 1]")


class FactCheckResponse(BaseModel):
    checks: list[FactCheck] = Field(description="All fact-check results")
    overall_assessment: str = Field(description="Overall assessment of this round")


class ModeratorResponse(BaseModel):
    round_summary: str = Field(description="Summary of this round")
    key_divergences: list[str] = Field(description="Key unresolved divergences")
    convergence_score: float = Field(description="Convergence score 0-1")
    should_continue: bool = Field(description="Whether to continue the debate")
    guidance_for_next_round: Optional[str] = Field(default=None, description="Focus guidance for the next round")
