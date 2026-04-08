---
description: "Use when creating or modifying agent classes (Advocate, Critic, FactChecker, Moderator). Covers BaseAgent inheritance, role binding, and run method structure."
applyTo: "src/agents/**"
---
# Agent Class Patterns

## BaseAgent

Located at `src/agents/base.py`. Provides:
- `async invoke(system_prompt, user_message, output_schema) -> tuple[Any, dict]`
- Retry logic (MAX_RETRIES=2): ValidationError → append format correction, other errors → log and retry
- Usage metadata extraction via `_extract_usage()` from `response.response_metadata`
- Model acquisition via `self.router.get_structured_model(self.role, schema)`

## Concrete Agent Pattern

Every agent follows this exact structure:

```python
class {Role}Agent(BaseAgent):
    role = "{role}"  # Must match ModelRouter keys

    async def run(self, state: DebateState) -> tuple[ResponseSchema, dict]:
        system_prompt = build_{role}_system_prompt(state)
        user_message = build_{role}_user_message(state)
        response, usage = await self.invoke(system_prompt, user_message, ResponseSchema)
        return response, usage
```

## Role-to-Schema Mapping

| Agent | Role String | Output Schema | Prompt Module |
|-------|------------|---------------|---------------|
| AdvocateAgent | `"advocate"` | `AgentResponse` | `src/prompts/advocate.py` |
| CriticAgent | `"critic"` | `AgentResponse` | `src/prompts/critic.py` |
| FactCheckerAgent | `"fact_checker"` | `FactCheckResponse` | `src/prompts/fact_checker.py` |
| ModeratorAgent | `"moderator"` | `ModeratorResponse` | `src/prompts/moderator.py` |

## Key Rules

1. **`role` class variable** must match the key used in `config.yaml` agents section and `ModelRouter`
2. **Constructor**: Takes only `router: ModelRouter` — all config flows through router
3. Agents are **stateless** — all state passed via `DebateState` parameter
4. Agent output is always a **tuple of (Pydantic model, usage dict)**
5. Agents do NOT update state directly — that's the node's job in `src/graph/nodes/`
