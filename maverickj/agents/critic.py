from maverickj.agents.base import BaseAgent
from maverickj.llm.router import ModelRouter
from maverickj.prompts.critic import build_critic_system_prompt, build_critic_user_message
from maverickj.schemas.agents import AgentResponse
from maverickj.schemas.debate import DebateState
from maverickj.schemas.supply_chain_engine import SupplyChainConfig


class CriticAgent(BaseAgent):
    role = "critic"

    def __init__(self, router: ModelRouter):
        super().__init__(router)

    async def run(self, state: DebateState) -> tuple[AgentResponse, dict, dict | None]:
        system_prompt = build_critic_system_prompt(state)
        user_message = build_critic_user_message(state)
        sc = state.supply_chain_config or SupplyChainConfig()
        if state.config.mode == "supply_chain" and sc.agent_tools.enabled:
            from maverickj.supply_chain.agents.supply_chain_agent import SupplyChainAgent
            from maverickj.supply_chain.paths import resolve_supply_chain_paths
            from maverickj.supply_chain.tools.langchain_tools import build_toolset
            from maverickj.supply_chain.tools.registry import ToolCallRegistry

            db_path, events_path, cache_path = resolve_supply_chain_paths(sc)
            tools = build_toolset(db_path=db_path, cache_path=cache_path, events_path=events_path)
            tool_calls = dict(state.tool_calls)
            registry = ToolCallRegistry(tool_calls)
            agent = SupplyChainAgent(self.router, self.role)
            max_calls = sc.agent_tools.max_tool_calls_per_turn
            response, usage = await agent.invoke_with_tools(
                system_prompt,
                user_message,
                AgentResponse,
                tools,
                max_tool_calls=max_calls,
                tool_registry=registry,
                invoked_at_round=state.current_round,
                invoked_by="critic",
                source="agent:risk_critic",
            )
            return response, usage, tool_calls
        response, usage = await self.invoke(system_prompt, user_message, AgentResponse)
        return response, usage, None
