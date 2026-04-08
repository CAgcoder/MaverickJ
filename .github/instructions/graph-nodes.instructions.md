---
description: "Use when creating or modifying LangGraph nodes, graph builder, or convergence conditions. Covers node function signatures, state update patterns, and conditional edge logic."
applyTo: "src/graph/**"
---
# LangGraph Graph Patterns

## Graph Structure

```
round_setup → advocate → critic → fact_checker → moderator
                                                    │
                                    should_continue(state)
                                     ├── "continue" → round_setup
                                     └── "terminate" → report → END
```

Built in `src/graph/builder.py` as `StateGraph(DebateState)`.

## Node Function Signature

Every node follows this exact pattern:

```python
async def {role}_node(state: DebateState, router: ModelRouter) -> dict:
    agent = {Role}Agent(router)
    response, usage = await agent.run(state)
    # Update registry, metadata, etc.
    return {
        "current_round_{role}": response,
        "argument_registry": registry.to_dict(),
        "metadata": state.metadata.model_copy(update={...}),
    }
```

- **Input**: `state: DebateState` + `router: ModelRouter` (injected via `functools.partial()`)
- **Output**: `dict` of state field updates — LangGraph merges these into state
- **Never mutate state directly** — always return a new dict

## Convergence Logic (`conditions.py`)

`should_continue(state)` returns `"terminate"` when ANY of:
1. `current_round >= max_rounds`
2. `status == DebateStatus.ERROR`
3. Latest moderator says `should_continue == False`
4. Last N rounds (N = `convergence_threshold`) all have `convergence_score >= convergence_score_target`

## Node Registration

Nodes are registered in builder with `partial()` for dependency injection:

```python
graph.add_node("advocate", partial(advocate_node, router=router))
```

## round_setup Node

- Increments `current_round`
- Clears transient fields: `current_round_advocate`, `current_round_critic`, etc.
- Appends new `DebateRound` to `state.rounds`

## report Node

- Invokes report generator agent with full debate transcript
- Sets `final_report` and `status` on state
