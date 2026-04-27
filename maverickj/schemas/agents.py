import json
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from maverickj.schemas.arguments import Argument, FactCheck, FactCheckVerdict, Rebuttal
import logging

logger = logging.getLogger(__name__)

# LLMs often wrap short Chinese emphasis with ASCII quotes: 严重度为"高"，… — breaks JSON strings.
# Third group includes fullwidth punctuation (e.g. U+FF0C ，) via \uff00-\uffef.
_CJK_STRAY_QUOTE = re.compile(
    r'([\u4e00-\u9fff\u3000-\u303f\uff08-\uff09])"([^"\n]{1,120})"([\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])',
)


def _repair_cjk_emphasis_quotes_in_json_text(s: str) -> str:
    """Replace CJK emphasis patterns like 为\"高\"， with corner quotes so json.loads can succeed."""
    cur = s
    for _ in range(16):
        nxt = _CJK_STRAY_QUOTE.sub(r"\1「\2」\3", cur)
        if nxt == cur:
            break
        cur = nxt
    return cur


def _strip_markdown_json_fence(raw: str) -> str:
    v_cleaned = raw.strip()
    if v_cleaned.startswith("```json"):
        v_cleaned = v_cleaned[7:]
    elif v_cleaned.startswith("```"):
        v_cleaned = v_cleaned[3:]
    if v_cleaned.endswith("```"):
        v_cleaned = v_cleaned[:-3]
    return v_cleaned.strip()


def _parse_json_array_string_with_fence_strip(raw: str) -> Optional[list[Any]]:
    """Parse a JSON array from an LLM-produced string; repair stray ASCII quotes inside Chinese prose."""
    v_cleaned = _strip_markdown_json_fence(raw)
    repaired = _repair_cjk_emphasis_quotes_in_json_text(v_cleaned)
    candidates = [v_cleaned]
    if repaired != v_cleaned:
        candidates.append(repaired)

    for i, candidate in enumerate(candidates):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                if i > 0:
                    logger.warning(
                        "JSON list parsed after CJK quote repair (stray ASCII quotes inside Chinese text)."
                    )
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _coerce_json_string_to_list(v: Any) -> Any:
    """If the LLM returns a list field as a JSON-encoded string, parse it first."""
    if isinstance(v, str):
        parsed = _parse_json_array_string_with_fence_strip(v)
        if parsed is not None:
            return parsed
        try:
            json.loads(_strip_markdown_json_fence(v))
        except (json.JSONDecodeError, ValueError) as last_err:
            logger.error(f"JSON 预处理解析失败: {last_err}\n问题字符串: {v}")
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
                    parsed = _parse_json_array_string_with_fence_strip(val)
                    if parsed is not None:
                        data[key] = parsed
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
                parsed = _parse_json_array_string_with_fence_strip(val)
                if parsed is not None:
                    data["checks"] = parsed
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
    feasibility_scores: dict[str, float] = Field(default_factory=dict, description="Feasibility scores by argument ID")
    relevance_scores: dict[str, float] = Field(default_factory=dict, description="Relevance scores by argument ID")

    @model_validator(mode="before")
    @classmethod
    def coerce_string_arrays(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("key_divergences")
            if isinstance(val, str):
                parsed = _parse_json_array_string_with_fence_strip(val)
                if parsed is not None:
                    data["key_divergences"] = parsed
        return data

    @field_validator("key_divergences", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: Any) -> Any:
        return _coerce_json_string_to_list(v)
