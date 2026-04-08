---
description: "Use when writing or modifying Pydantic v2 schemas for debate state, agent responses, arguments, or reports. Covers field conventions, enum patterns, and structured output compatibility."
applyTo: "src/schemas/**"
---
# Schema Design Rules

## Pydantic v2 Conventions

- All models inherit `BaseModel` (never `dataclass` or plain dict)
- Field descriptions required for LLM-facing schemas: `Field(description="...")`
- Use `default=None` for optional fields, `default_factory=list` for mutable defaults
- Enum fields use `str` mixin: `class Status(str, Enum)`

## Existing Schema Structure

| File | Purpose | Key Models |
|------|---------|------------|
| `agents.py` | LLM response parsing | `AgentResponse`, `FactCheckResponse`, `ModeratorResponse` |
| `arguments.py` | Argument lifecycle | `Argument`, `Rebuttal`, `FactCheck`, `ArgumentRecord`, `ArgumentStatus` |
| `debate.py` | Graph state | `DebateState`, `DebateRound`, `DebateConfig`, `DebateMetadata`, `DebateStatus` |
| `report.py` | Final output | `DecisionReport`, `ScoredArgument`, `Recommendation`, `DebateStats` |
| `config.py` | Configuration | `ModelAssignment`, `AgentModelConfig`, `DebateEngineConfig` |

## Key Rules

1. **DebateState** is the LangGraph central state — transient fields (`current_round_*`) are cleared each round in `round_setup` node
2. **AgentResponse** is shared by Advocate and Critic — differentiated by `agent_role` field
3. **Argument IDs** must follow `{ROLE}-R{round}-{index}` pattern — describe this in Field descriptions
4. **ArgumentStatus** transitions: ACTIVE → REBUTTED (by opponent rebuttal), CONCEDED (by self), MODIFIED (by self with changes)
5. **Immutable updates**: Use `state.metadata.model_copy(update={...})` — never mutate state directly
6. Schemas used for structured LLM output must have clear `description` on every field for model guidance
7. `FactCheckVerdict` enum values: VALID, FLAWED, NEEDS_CONTEXT, UNVERIFIABLE — FLAWED auto-triggers REBUTTED status
