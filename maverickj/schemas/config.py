from typing import Optional

from pydantic import BaseModel, Field

from maverickj.schemas.debate import DebateConfig
from maverickj.schemas.supply_chain_engine import SupplyChainConfig


class ModelAssignment(BaseModel):
    provider: str = Field(description="claude | openai | gemini")
    model: str = Field(description="Model name")
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    fallback: Optional["ModelAssignment"] = None


class AgentModelConfig(BaseModel):
    advocate: ModelAssignment
    critic: ModelAssignment
    fact_checker: ModelAssignment
    moderator: ModelAssignment
    report_generator: ModelAssignment
    fusion_synthesizer: Optional[ModelAssignment] = None
    convergence_critic: Optional[ModelAssignment] = None


class DebateEngineConfig(BaseModel):
    """Top-level config, loaded from YAML."""
    default_provider: str = "claude"
    default_model: str = "claude-sonnet-4-20250514"
    default_temperature: float = 0.7
    default_max_tokens: int = 8192
    agents: Optional[AgentModelConfig] = None
    debate: DebateConfig = Field(default_factory=DebateConfig)
    supply_chain: SupplyChainConfig = Field(default_factory=SupplyChainConfig)
