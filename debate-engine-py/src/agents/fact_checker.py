from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.prompts.fact_checker import build_fact_checker_system_prompt, build_fact_checker_user_message
from src.schemas.agents import FactCheckResponse
from src.schemas.debate import DebateState


class FactCheckerAgent(BaseAgent):
    role = "fact_checker"

    def __init__(self, router: ModelRouter):
        super().__init__(router)

    async def run(self, state: DebateState) -> tuple[FactCheckResponse, dict]:
        system_prompt = build_fact_checker_system_prompt(state)
        user_message = build_fact_checker_user_message(state)
        response, usage = await self.invoke(system_prompt, user_message, FactCheckResponse)
        return response, usage
