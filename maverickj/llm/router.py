from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from maverickj.schemas.config import DebateEngineConfig, ModelAssignment
from maverickj.llm.factory import create_model


AGENT_ROLES = ["advocate", "critic", "fact_checker", "moderator", "report_generator"]


class ModelRouter:
    def __init__(self, config: DebateEngineConfig):
        self.config = config
        self._models: dict[str, BaseChatModel] = {}
        self._init_models()

    def _init_models(self) -> None:
        if self.config.agents:
            for role in AGENT_ROLES:
                assignment = getattr(self.config.agents, role)
                model = create_model(assignment)
                if assignment.fallback:
                    fallback_model = create_model(assignment.fallback)
                    model = model.with_fallbacks([fallback_model])
                self._models[role] = model
        else:
            default = ModelAssignment(
                provider=self.config.default_provider,
                model=self.config.default_model,
                temperature=self.config.default_temperature,
            )
            default_model = create_model(default)
            for role in AGENT_ROLES:
                self._models[role] = default_model

    def get_model(self, agent_role: str) -> BaseChatModel:
        if agent_role not in self._models:
            raise ValueError(f"未知的 agent 角色: {agent_role}")
        return self._models[agent_role]

    def get_structured_model(self, agent_role: str, schema: type[BaseModel]) -> Runnable:
        """返回带结构化输出的模型（使用 json_mode 避免 Claude XML tool-call 解析异常）"""
        model = self.get_model(agent_role)
        return model.with_structured_output(schema, method="json_mode")
