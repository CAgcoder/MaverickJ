from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.arguments import Argument, FactCheck, FactCheckVerdict, Rebuttal


class AgentResponse(BaseModel):
    """Advocate 和 Critic 的通用输出格式"""
    agent_role: str = Field(description="Agent 角色: advocate 或 critic")
    arguments: list[Argument] = Field(description="本轮提出的论点")
    rebuttals: list[Rebuttal] = Field(default_factory=list, description="对对方论点的反驳")
    concessions: list[str] = Field(default_factory=list, description="承认对方有道理的部分")
    confidence_shift: float = Field(default=0.0, description="本轮立场变化 [-1, 1]")


class FactCheckResponse(BaseModel):
    checks: list[FactCheck] = Field(description="所有校验结果")
    overall_assessment: str = Field(description="整体评估")


class ModeratorResponse(BaseModel):
    round_summary: str = Field(description="本轮总结")
    key_divergences: list[str] = Field(description="当前关键分歧")
    convergence_score: float = Field(description="收敛分数 0-1")
    should_continue: bool = Field(description="是否继续辩论")
    guidance_for_next_round: Optional[str] = Field(default=None, description="下一轮焦点引导")
