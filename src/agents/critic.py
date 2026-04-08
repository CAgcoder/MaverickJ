from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.prompts.critic import build_critic_system_prompt, build_critic_user_message
from src.schemas.agents import AgentResponse
from src.schemas.debate import DebateState


class CriticAgent(BaseAgent):
    role = "critic"

    def __init__(self, router: ModelRouter):
        super().__init__(router)

    async def run(self, state: DebateState) -> tuple[AgentResponse, dict]:
        system_prompt = build_critic_system_prompt(state)
        user_message = build_critic_user_message(state)
        response, usage = await self.invoke(system_prompt, user_message, AgentResponse)
        return response, usage
