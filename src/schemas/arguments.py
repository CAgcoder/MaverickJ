from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ArgumentStatus(str, Enum):
    ACTIVE = "active"
    REBUTTED = "rebutted"
    CONCEDED = "conceded"
    MODIFIED = "modified"


class Argument(BaseModel):
    id: str = Field(description="论点 ID，格式如 ADV-R1-01 或 CRT-R1-01")
    claim: str = Field(description="论点主张")
    reasoning: str = Field(description="推理过程")
    evidence: Optional[str] = Field(default=None, description="支撑证据")
    status: ArgumentStatus = Field(default=ArgumentStatus.ACTIVE, description="论点状态")


class Rebuttal(BaseModel):
    target_argument_id: str = Field(description="反驳目标论点 ID")
    counter_claim: str = Field(description="反驳主张")
    reasoning: str = Field(description="反驳推理")


class FactCheckVerdict(str, Enum):
    VALID = "valid"
    FLAWED = "flawed"
    NEEDS_CONTEXT = "needs_context"
    UNVERIFIABLE = "unverifiable"


class FactCheck(BaseModel):
    target_argument_id: str = Field(description="校验目标论点 ID")
    verdict: FactCheckVerdict = Field(description="校验判定")
    explanation: str = Field(description="校验说明")
    correction: Optional[str] = Field(default=None, description="修正建议")
    fallacy_type: Optional[str] = Field(default=None, description="谬误类型")


class ArgumentRecord(BaseModel):
    """ArgumentRegistry 中存储的完整论点生命周期"""
    argument: Argument
    raised_in_round: int
    raised_by: str  # "advocate" | "critic"
    rebuttals: list[Rebuttal] = []
    fact_checks: list[FactCheck] = []
    modification_history: list[str] = []
