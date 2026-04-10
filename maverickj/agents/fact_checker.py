from maverickj.agents.base import BaseAgent
from maverickj.llm.router import ModelRouter
from maverickj.prompts.fact_checker import build_fact_checker_system_prompt, build_fact_checker_user_message
from maverickj.schemas.agents import FactCheckResponse
from maverickj.schemas.debate import DebateState


class FactCheckerAgent(BaseAgent):
    role = "fact_checker"

    def __init__(self, router: ModelRouter):
        super().__init__(router)

    async def run(self, state: DebateState) -> tuple[FactCheckResponse, dict]:
        system_prompt = build_fact_checker_system_prompt(state)
        user_message = build_fact_checker_user_message(state)
        response, usage = await self.invoke(system_prompt, user_message, FactCheckResponse)
        return response, usage
