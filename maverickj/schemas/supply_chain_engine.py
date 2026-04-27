"""Supply-chain engine settings (kept separate from debate.py to avoid import cycles)."""

from pydantic import BaseModel, Field


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
