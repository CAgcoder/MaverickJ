---
description: "Use when writing or modifying tests for the debate engine. Covers pytest patterns, async test conventions, fixture usage, and test structure."
applyTo: "tests/**"
---
# Testing Conventions

## Framework

- **pytest** with `pytest-asyncio` (asyncio_mode = auto)
- All async test functions are auto-detected — no `@pytest.mark.asyncio` needed

## Directory Structure

Tests mirror `maverickj/` layout:
```
tests/
├── conftest.py            # Shared fixtures
├── fixtures/              # JSON mock data
│   ├── mock_advocate_response.json
│   └── mock_critic_response.json
├── test_agents/           # Agent class tests
├── test_core/             # ArgumentRegistry, TranscriptManager
├── test_graph/            # Conditions, builder
└── test_output/           # Renderer
```

## Fixtures (`conftest.py`)

Key fixtures use real Pydantic models (not mocks):
- `debate_config` → `DebateConfig`
- `engine_config` → `DebateEngineConfig`
- `sample_debate_state` → Full `DebateState` with rounds
- `sample_debate_round` → `DebateRound` with all agent responses

## Key Patterns

1. **Use real Pydantic models** — construct actual schema objects, not dicts
2. **Test state transitions** — verify ArgumentStatus changes (ACTIVE → REBUTTED, etc.)
3. **Test convergence logic** — parameterize with various state combinations
4. **No LLM calls in unit tests** — mock at the agent or router level
5. **Fixture JSON files** in `tests/fixtures/` for complex response data

## Running Tests

```bash
pytest                           # All tests
pytest tests/test_core/          # Specific module
pytest -v                        # Verbose
pytest -k "test_convergence"     # By name pattern
```
