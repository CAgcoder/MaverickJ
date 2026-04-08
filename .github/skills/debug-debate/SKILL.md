---
name: debug-debate
description: "Debug debate engine issues: convergence failures, agent errors, graph execution problems, LLM parsing failures, or unexpected debate behavior. Use when debate gets stuck, produces invalid output, or crashes during execution."
argument-hint: "Describe the issue (e.g., debate never converges, agent parsing error)"
---
# Debug Debate Engine

## When to Use

- Debate never converges (runs to max_rounds without resolution)
- Agent produces invalid structured output (ValidationError)
- Graph execution fails or hangs
- Unexpected argument lifecycle transitions
- Cost anomalies or token budget issues

## Diagnostic Procedures

### Issue: Debate Never Converges

1. **Check convergence config** in `config.yaml`:
   ```yaml
   debate:
     convergence_threshold: 2       # Consecutive rounds needed
     convergence_score_target: 0.8  # Score threshold (0-1)
   ```
2. **Inspect moderator responses** — look at `convergence_score` in each round
3. **Check `should_continue()` logic** in `src/graph/conditions.py`:
   - Needs N consecutive rounds with score ≥ target
   - OR moderator sets `should_continue: false`
4. **Common fix**: Lower `convergence_score_target` or reduce `convergence_threshold`

### Issue: Agent ValidationError (Structured Output Failure)

1. **Check the Pydantic schema** being passed to `with_structured_output()`
2. **Look for enum mismatches** — LLM may return values not in the enum
3. **Inspect the retry mechanism** in `BaseAgent.invoke()`:
   - MAX_RETRIES=2
   - ValidationError → correction instruction appended to next attempt
4. **Check prompt clarity** — ensure output format is unambiguous in system prompt
5. **Model capability** — some models handle structured output worse; try a stronger model

### Issue: Graph Execution Error

1. **Check `round_setup` node** — ensure all transient fields are properly cleared
2. **Check node return dicts** — every node must return a `dict` with valid state keys
3. **Verify `functools.partial()`** injection in `src/graph/builder.py`
4. **Check state field types** — LangGraph requires matching Pydantic types

### Issue: Argument ID Conflicts

1. **Check prompt templates** — IDs must follow `{ROLE}-R{round}-{index}` pattern
2. **Verify `ArgumentRegistry.register()`** — should not allow duplicate IDs
3. **Look at round_setup** — ensure `current_round` increments correctly

### Issue: Token Budget / Cost Anomalies

1. **Check `TranscriptManager`** — `transcript_compression_after_round` setting
2. If rounds > threshold but compression isn't kicking in, inspect `build_context_for_agent()`
3. **Monitor `DebateMetadata.total_tokens_used`** — compare against expected per-round usage
4. **Review `MODEL_PRICING`** — ensure model names match exactly

## Quick Diagnostic Commands

```bash
# Run with verbose logging
python -m src.main "test question" 2>&1 | head -100

# Check if models load correctly
python -c "
from src.llm.router import ModelRouter
from src.schemas.config import DebateEngineConfig
config = DebateEngineConfig()
router = ModelRouter(config)
print('Models loaded successfully')
"

# Test a single agent in isolation
python -c "
import asyncio
from src.agents.advocate import AdvocateAgent
# ... construct minimal state and test
"

# Run specific test suites
pytest tests/test_graph/test_conditions.py -v
pytest tests/test_core/test_argument_registry.py -v
```

## State Inspection Pattern

When debugging, add temporary state inspection in nodes:

```python
async def advocate_node(state: DebateState, router: ModelRouter) -> dict:
    import logging
    logging.info(f"Round {state.current_round}, registry size: {len(state.argument_registry)}")
    logging.info(f"Prior moderator guidance: {state.rounds[-1].moderator.guidance_for_next_round if state.rounds else 'N/A'}")
    # ... rest of node
```
