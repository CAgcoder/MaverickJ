# Auto-Gangjing — Project Guidelines

## Identity

Multi-agent debate-driven decision engine. Four AI agents (Advocate, Critic, Fact-Checker, Moderator) conduct structured adversarial debate via LangGraph, producing decision reports.

## Tech Stack

- Python 3.12+ (use modern syntax: `list[T]`, `dict[K, V]`, `X | None`)
- LangGraph 0.3+ (stateful multi-agent orchestration)
- LangChain Core 0.3+ (unified LLM abstraction)
- Pydantic v2 (all data models, structured LLM output)
- Rich (CLI terminal UI)
- Jinja2 (report templates)

## Build & Test

```bash
pip install -e .                  # Install in dev mode
pip install -e ".[dev]"           # With dev deps (pytest, ruff)
pytest                            # Run tests (asyncio_mode=auto)
ruff check src/ tests/            # Lint
ruff format src/ tests/           # Format
debate-interactive                # Run interactive CLI
python -m src.main "question"     # Run batch mode
docker compose build && docker compose run --rm debate  # Docker
```

## Architecture (5 layers)

1. **Agents** (`src/agents/`): BaseAgent → concrete agents. Each has `async run(state) -> (response, usage)`
2. **Graph** (`src/graph/`): LangGraph StateGraph with nodes: round_setup → advocate → critic → fact_checker → moderator → [continue|report]
3. **Schemas** (`src/schemas/`): Pydantic v2 models for state, arguments, agent responses, reports
4. **LLM** (`src/llm/`): ModelRouter + factory pattern. Per-agent model assignment with fallback
5. **Output** (`src/output/`): Rich console streaming + Markdown report rendering

## Core Conventions

- **Async everywhere**: All agent methods and LLM calls are async. Use `await model.ainvoke()`, never sync `.invoke()`
- **State immutability**: Graph nodes return `dict` of changes. Use `model_copy(update={...})` for nested Pydantic updates
- **Argument IDs**: Format `{ROLE}-R{round}-{index}` (e.g., `ADV-R1-01`, `CRT-R2-03`). Enforced in prompts and schemas
- **Structured output**: All LLM responses parsed via `model.with_structured_output(PydanticSchema)`
- **Private helpers**: Prefix with `_` (e.g., `_format_history()`, `_extract_usage()`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`, `MODEL_PRICING`)
- **Retry pattern**: ValidationError → append correction instruction and retry (MAX_RETRIES=2)
- **Type annotations**: Required on all function signatures. Use `Optional[T] = None` for nullable fields

## Key Patterns

- **Agent pattern**: Inherit `BaseAgent`, set `role = "..."`, override `async def run(state: DebateState)`
- **Node pattern**: `async def {role}_node(state: DebateState, router: ModelRouter) -> dict`; router injected via `functools.partial()`
- **Prompt pattern**: Each agent has `build_{role}_system_prompt(state)` + `build_{role}_user_message(state)` in `src/prompts/`
- **Registry pattern**: `ArgumentRegistry` tracks argument lifecycle (ACTIVE → REBUTTED/CONCEDED/MODIFIED)

## File Organization

- One class per file for agents, nodes, schemas
- Prompts co-located by agent role in `src/prompts/`
- Tests mirror `src/` structure under `tests/`
- Examples in `examples/` follow: load config → define question → run_debate → render → save
