"""Decision-matrix row types for supply-chain reports (phase 7+ rendering)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DecisionOption(BaseModel):
    path_name: str = Field(description="Option label, e.g. stay local vs switch to SEA")
    expected_tco_usd: float | None = Field(default=None, description="Expected annual TCO or scenario total")
    implementation_cost_usd: float | None = Field(default=None, description="One-time switch / capex")
    risk_warnings: list[str] = Field(default_factory=list)
    supporting_tool_calls: list[str] = Field(default_factory=list, description="Referenced TC-* IDs")


class CircuitBreaker(BaseModel):
    trigger_condition: str = Field(description="Human-readable trigger, e.g. WTI above $95/bbl")
    trigger_metric: str = Field(description="Metric key, e.g. CL=F")
    threshold_value: str = Field(description="Numeric or comparative threshold")
    fallback_action: str = Field(description="What to do when triggered")
    rationale: str = Field(default="", description="Why this breaker matters")
