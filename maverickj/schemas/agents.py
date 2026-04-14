import json
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from maverickj.schemas.arguments import Argument, FactCheck, FactCheckVerdict, Rebuttal


def _coerce_json_string_to_list(v: Any) -> Any:
    """If the LLM returns a list field as a JSON-encoded string, parse it first."""
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return v


class AgentResponse(BaseModel):
    """Common output format for Advocate and Critic agents."""
    agent_role: str = Field(description="Agent role: advocate or critic")
    arguments: list[Argument] = Field(description="Arguments raised this round")
    rebuttals: list[Rebuttal] = Field(default_factory=list, description="Rebuttals against the opponent's arguments")
    concessions: list[str] = Field(default_factory=list, description="Points conceded to the opponent")
    confidence_shift: float = Field(default=0.0, description="Confidence change this round [-1, 1]")

    @field_validator("arguments", "rebuttals", "concessions", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: Any) -> Any:
        return _coerce_json_string_to_list(v)


class FactCheckResponse(BaseModel):
    checks: list[FactCheck] = Field(default_factory=list, description="All fact-check results")
    overall_assessment: str = Field(default="", description="Overall assessment of this round")

    @field_validator("checks", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: Any) -> Any:
        return _coerce_json_string_to_list(v)


class ModeratorResponse(BaseModel):
    round_summary: str = Field(description="Summary of this round")
    key_divergences: list[str] = Field(description="Key unresolved divergences")
    convergence_score: float = Field(description="Convergence score 0-1")
    should_continue: bool = Field(description="Whether to continue the debate")
    guidance_for_next_round: Optional[str] = Field(default=None, description="Focus guidance for the next round")

    @field_validator("key_divergences", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: Any) -> Any:
        return _coerce_json_string_to_list(v)
