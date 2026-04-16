import json
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def coerce_string_arrays(cls, data: Any) -> Any:
        """Run before field validators: convert any JSON-string list fields to actual lists.
        Needed because some LangChain structured-output parsers bypass field-level validators."""
        if isinstance(data, dict):
            for key in ("arguments", "rebuttals", "concessions"):
                val = data.get(key)
                if isinstance(val, str):
                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, list):
                            data[key] = parsed
                    except (json.JSONDecodeError, ValueError):
                        pass
        return data

    @field_validator("arguments", "rebuttals", "concessions", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: Any) -> Any:
        return _coerce_json_string_to_list(v)


class FactCheckResponse(BaseModel):
    checks: list[FactCheck] = Field(default_factory=list, description="All fact-check results")
    overall_assessment: str = Field(default="", description="Overall assessment of this round")

    @model_validator(mode="before")
    @classmethod
    def coerce_string_arrays(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("checks")
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        data["checks"] = parsed
                except (json.JSONDecodeError, ValueError):
                    pass
        return data

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

    @model_validator(mode="before")
    @classmethod
    def coerce_string_arrays(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("key_divergences")
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        data["key_divergences"] = parsed
                except (json.JSONDecodeError, ValueError):
                    pass
        return data

    @field_validator("key_divergences", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: Any) -> Any:
        return _coerce_json_string_to_list(v)
