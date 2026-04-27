from typing import Optional

from pydantic import BaseModel, Field

from maverickj.schemas.debate import DebateConfig


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


class MarketDataConfig(BaseModel):
    tickers: list[str] = Field(default_factory=lambda: ["CL=F", "NG=F", "EUR=X"])
    cache_ttl_hours: int = 6
    offline_mode: bool = False


class MonteCarloConfig(BaseModel):
    simulations: int = 1000
    confidence_levels: list[float] = Field(default_factory=lambda: [0.5, 0.95])


class FusionConfig(BaseModel):
    composite_score_threshold: float = 8.0
    factuality_score_threshold: float = 7.0
    critique_max_rounds: int = 1


class AgentToolsConfig(BaseModel):
    enabled: bool = True
    max_tool_calls_per_turn: int = 5


class SupplyChainConfig(BaseModel):
    data_path: str = "./maverickj/supply_chain/data"
    market_data: MarketDataConfig = Field(default_factory=MarketDataConfig)
    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    agent_tools: AgentToolsConfig = Field(default_factory=AgentToolsConfig)


class DebateEngineConfig(BaseModel):
    """Top-level config, loaded from YAML."""
    default_provider: str = "claude"
    default_model: str = "claude-sonnet-4-20250514"
    default_temperature: float = 0.7
    default_max_tokens: int = 8192
    agents: Optional[AgentModelConfig] = None
    debate: DebateConfig = Field(default_factory=DebateConfig)
    supply_chain: SupplyChainConfig = Field(default_factory=SupplyChainConfig)
