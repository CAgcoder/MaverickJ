from typing import Optional

from pydantic import BaseModel, Field

from maverickj.schemas.debate import DebateConfig


class ModelAssignment(BaseModel):
    provider: str = Field(description="claude | openai | gemini")
    model: str = Field(description="模型名称")
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    fallback: Optional["ModelAssignment"] = None


class AgentModelConfig(BaseModel):
    advocate: ModelAssignment
    critic: ModelAssignment
    fact_checker: ModelAssignment
    moderator: ModelAssignment
    report_generator: ModelAssignment


class DebateEngineConfig(BaseModel):
    """顶层配置，从 YAML 加载"""
    default_provider: str = "claude"
    default_model: str = "claude-sonnet-4-20250514"
    default_temperature: float = 0.7
    agents: Optional[AgentModelConfig] = None
    debate: DebateConfig = DebateConfig()
