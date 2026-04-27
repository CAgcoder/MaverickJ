"""Fusion / ToT schemas for supply-chain termination phase."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HighScoreArgumentEntry(BaseModel):
    argument_id: str
    composite_score: float = Field(ge=0.0, le=10.0)
    factuality_score: float = Field(ge=0.0, le=10.0)


class FusionDraft(BaseModel):
    high_score_arguments: list[HighScoreArgumentEntry] = Field(default_factory=list)
    proposed_consensus: str = Field(description="Single synthesized consensus narrative")
    consensus_actions: list[str] = Field(default_factory=list, description="Concrete next steps")
    open_questions: list[str] = Field(default_factory=list)


class ConvergenceCritique(BaseModel):
    perspective: Literal["cost_advocate", "risk_critic"]
    critique_points: list[str] = Field(default_factory=list, description="1–3 constructive critiques of the draft")
    final_endorsement: bool = Field(description="Whether this side endorses moving forward with the draft")


class FusedDecision(BaseModel):
    final_consensus: str
    accepted_amendments: list[str] = Field(default_factory=list)
    rejected_amendments_with_reason: list[str] = Field(
        default_factory=list,
        description="Each entry: amendment — reason rejected",
    )
    remaining_disagreements: list[str] = Field(
        default_factory=list,
        description="Feeds minority_report in the final report",
    )


class ConvergenceCritiqueOutput(BaseModel):
    """Structured output for one critique pass (no new arguments)."""

    critique_points: list[str] = Field(default_factory=list)
    final_endorsement: bool = False
