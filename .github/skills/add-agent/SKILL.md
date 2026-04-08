---
name: add-agent
description: "Add a new debate agent to the engine. Use when creating a new agent role, extending the debate with additional perspectives, or implementing a new specialized agent (e.g., Devil's Advocate, Domain Expert, Risk Assessor)."
argument-hint: "Describe the new agent role and its purpose"
---
# Add a New Debate Agent

## When to Use

- Adding a new agent role to the debate system (e.g., Risk Assessor, Domain Expert)
- Extending the 4-agent debate with additional perspectives
- Creating a specialized agent for a specific domain

## Procedure

Follow these steps **in order**. Each step depends on the previous.

### Step 1: Define the Response Schema

Create or reuse a Pydantic v2 schema in `src/schemas/agents.py`:

```python
class NewAgentResponse(BaseModel):
    """Structured response for the NewAgent role."""
    agent_role: str = Field(description="Agent role identifier")
    # Add role-specific fields
```

If the new agent has a similar output structure to Advocate/Critic, reuse `AgentResponse`.

### Step 2: Create the Prompt Builders

Create `src/prompts/{new_role}.py` with two functions:

```python
def build_{new_role}_system_prompt(state: DebateState) -> str:
    """Define role identity, behavioral rules, output format."""

def build_{new_role}_user_message(state: DebateState) -> str:
    """Compose question + context + history + guidance."""
```

See [prompt conventions](../../.github/instructions/prompts.instructions.md) for detailed patterns.

### Step 3: Create the Agent Class

Create `src/agents/{new_role}.py`:

```python
from src.agents.base import BaseAgent
from src.schemas.debate import DebateState

class NewRoleAgent(BaseAgent):
    role = "{new_role}"  # Must match config.yaml key

    async def run(self, state: DebateState) -> tuple[ResponseSchema, dict]:
        system_prompt = build_{new_role}_system_prompt(state)
        user_message = build_{new_role}_user_message(state)
        response, usage = await self.invoke(system_prompt, user_message, ResponseSchema)
        return response, usage
```

### Step 4: Create the Graph Node

Create `src/graph/nodes/{new_role}.py`:

```python
from src.llm.router import ModelRouter
from src.schemas.debate import DebateState

async def {new_role}_node(state: DebateState, router: ModelRouter) -> dict:
    agent = NewRoleAgent(router)
    response, usage = await agent.run(state)
    # Update ArgumentRegistry if the agent creates/modifies arguments
    return {
        "current_round_{new_role}": response,
        "metadata": state.metadata.model_copy(update={...}),
    }
```

### Step 5: Add State Fields

In `src/schemas/debate.py`:
1. Add `current_round_{new_role}: Optional[ResponseSchema] = None` to `DebateState`
2. Add `{new_role}: Optional[ResponseSchema] = None` to `DebateRound`

### Step 6: Wire into the Graph

In `src/graph/builder.py`:
1. Import the new node function
2. Add node: `graph.add_node("{new_role}", partial({new_role}_node, router=router))`
3. Add edges to position the new node in the execution chain
4. Update `round_setup` to clear the new transient field

### Step 7: Add Console Output

In `src/output/stream.py`:
1. Add entry to `AGENT_STYLES` dict with color/icon/label
2. Create `print_{new_role}_result()` function

### Step 8: Update Config

In `src/schemas/config.py`:
1. Add `{new_role}: Optional[ModelAssignment] = None` to `AgentModelConfig`

### Step 9: Export & Test

1. Update `__init__.py` files for agents, nodes, prompts
2. Write tests in `tests/test_agents/test_{new_role}.py`
3. Run `pytest` and `ruff check src/` to validate

## Checklist

- [ ] Schema defined or reused
- [ ] Prompt builders created (system + user)
- [ ] Agent class inherits BaseAgent with correct `role`
- [ ] Graph node follows `async def ...(state, router) -> dict` pattern
- [ ] DebateState has transient field + DebateRound has storage field
- [ ] Node wired into graph builder with correct edge ordering
- [ ] Console output styled
- [ ] Config schema updated
- [ ] Tests written and passing
