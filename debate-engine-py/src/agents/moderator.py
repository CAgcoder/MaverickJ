from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.prompts.moderator import build_moderator_system_prompt, build_moderator_user_message
from src.schemas.agents import ModeratorResponse
from src.schemas.debate import DebateState


class ModeratorAgent(BaseAgent):
    role = "moderator"

    def __init__(self, router: ModelRouter):
        super().__init__(router)

    async def run(self, state: DebateState) -> tuple[ModeratorResponse, dict]:
        system_prompt = build_moderator_system_prompt(state)
        user_message = build_moderator_user_message(state)
        response, usage = await self.invoke(system_prompt, user_message, ModeratorResponse)
        return response, usage
