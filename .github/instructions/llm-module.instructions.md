---
description: "Use when working with the LLM module: ModelRouter, model factory, cost calculation, or adding/configuring LLM providers. Covers factory dispatch, router caching, structured output, and fallback patterns."
applyTo: "maverickj/llm/**"
---
# LLM Module Patterns

## Module Structure

| File | Purpose |
|------|---------|
| `factory.py` | Creates LangChain `BaseChatModel` instances by provider |
| `router.py` | `ModelRouter` — caches models, dispatches by agent role |
| `cost.py` | Token pricing and cost calculation |

## Factory Pattern (`factory.py`)

```python
def create_model(assignment: ModelAssignment) -> BaseChatModel:
```

- Dispatches by `assignment.provider`: `"claude"` → `ChatAnthropic`, `"openai"` → `ChatOpenAI`, `"gemini"` → `ChatGoogleGenerativeAI`
- Uses dynamic imports (lazy loading)
- Applies `temperature`, `max_tokens` from `ModelAssignment`

## ModelRouter (`router.py`)

- **Singleton cache**: `_models: dict[str, BaseChatModel]` — models created once in `__init__`
- **Per-role assignment**: If `agents` config provided, each agent role gets its own model config
- **Fallback**: `model.with_fallbacks([fallback_model])` when `ModelAssignment.fallback` is set
- **Key method**: `get_structured_model(agent_role, schema)` → returns `model.with_structured_output(schema)`
- **Lazy init**: `_init_models()` loads all models at construction time

## Structured Output

All LLM calls use structured output:
```python
structured_model = router.get_structured_model("advocate", AgentResponse)
response = await structured_model.ainvoke(messages)
```

This ensures Pydantic schema validation on every LLM response.

## Cost Tracking

- `MODEL_PRICING` dict: `{model_name: {"input": price_per_1M, "output": price_per_1M}}`
- `calculate_cost(model_name, input_tokens, output_tokens) -> float`
- Accumulated in `DebateMetadata.total_cost_usd` through node updates

## Adding a New Provider

1. Add provider case in `factory.py` `create_model()`
2. Add pricing to `MODEL_PRICING` in `cost.py`
3. Add provider option to `ModelAssignment.provider` field in `maverickj/schemas/config.py`
4. Install langchain integration package, add to `pyproject.toml`
