from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from maverickj.schemas.config import DebateEngineConfig, ModelAssignment
from maverickj.llm.factory import create_model


AGENT_ROLES = [
    "advocate",
    "critic",
    "fact_checker",
    "moderator",
    "report_generator",
    "fusion_synthesizer",
    "convergence_critic",
]


class ModelRouter:
    def __init__(self, config: DebateEngineConfig):
        self.config = config
        self._models: dict[str, BaseChatModel] = {}
        self._init_models()

    def _init_models(self) -> None:
        if self.config.agents:
            report_model: BaseChatModel | None = None
            for role in AGENT_ROLES:
                assignment = getattr(self.config.agents, role, None)
                if assignment is None:
                    if report_model is None:
                        report_assignment = getattr(self.config.agents, "report_generator")
                        report_model = create_model(report_assignment)
                        if report_assignment.fallback:
                            fallback_model = create_model(report_assignment.fallback)
                            report_model = report_model.with_fallbacks([fallback_model])
                    self._models[role] = report_model
                    continue
                model = create_model(assignment)
                if assignment.fallback:
                    fallback_model = create_model(assignment.fallback)
                    model = model.with_fallbacks([fallback_model])
                self._models[role] = model
                if role == "report_generator":
                    report_model = model
        else:
            default = ModelAssignment(
                provider=self.config.default_provider,
                model=self.config.default_model,
                temperature=self.config.default_temperature,
                max_tokens=self.config.default_max_tokens,
            )
            default_model = create_model(default)
            for role in AGENT_ROLES:
                self._models[role] = default_model

    def get_model(self, agent_role: str) -> BaseChatModel:
        if agent_role not in self._models:
            raise ValueError(f"Unknown agent role: {agent_role}")
        return self._models[agent_role]

    def get_structured_model(self, agent_role: str, schema: type[BaseModel]) -> Runnable:
        """Return a model with structured output bound to the given Pydantic schema."""
        model = self.get_model(agent_role)
        return model.with_structured_output(schema)
