from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ArgumentStatus(str, Enum):
    ACTIVE = "active"
    REBUTTED = "rebutted"
    CONCEDED = "conceded"
    MODIFIED = "modified"


class Argument(BaseModel):
    id: str = Field(description="Argument ID, e.g. ADV-R1-01 or CRT-R1-01")
    claim: str = Field(description="Argument claim")
    reasoning: str = Field(description="Reasoning process")
    evidence: Optional[str] = Field(default=None, description="Supporting evidence")
    tool_call_ids: list[str] = Field(default_factory=list, description="Referenced tool call IDs")
    status: ArgumentStatus = Field(default=ArgumentStatus.ACTIVE, description="Argument status")


class Rebuttal(BaseModel):
    target_argument_id: str = Field(description="ID of the argument being rebutted")
    counter_claim: str = Field(description="Counter-claim")
    reasoning: str = Field(description="Rebuttal reasoning")


class FactCheckVerdict(str, Enum):
    VALID = "valid"
    FLAWED = "flawed"
    NEEDS_CONTEXT = "needs_context"
    UNVERIFIABLE = "unverifiable"


class FactCheck(BaseModel):
    target_argument_id: str = Field(description="ID of the argument being fact-checked")
    verdict: FactCheckVerdict = Field(description="Fact-check verdict")
    explanation: str = Field(description="Explanation of the verdict")
    correction: Optional[str] = Field(default=None, description="Suggested correction")
    fallacy_type: Optional[str] = Field(default=None, description="Type of logical fallacy, if any")
    factuality_score: Optional[float] = Field(default=None, description="Factuality score [0, 10]")
    logic_score: Optional[float] = Field(default=None, description="Logic score [0, 10]")


class ArgumentRecord(BaseModel):
    """Complete argument lifecycle record stored in the ArgumentRegistry."""
    argument: Argument
    raised_in_round: int
    raised_by: str  # "advocate" | "critic"
    rebuttals: list[Rebuttal] = []
    fact_checks: list[FactCheck] = []
    modification_history: list[str] = []
