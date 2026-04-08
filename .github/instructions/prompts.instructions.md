---
description: "Use when writing or modifying prompt builder functions for debate agents. Covers system/user prompt structure, language detection, history formatting, and argument ID conventions."
applyTo: "src/prompts/**"
---
# Prompt Engineering Conventions

## Builder Function Pattern

Each agent role has exactly two functions in `src/prompts/{role}.py`:

```python
def build_{role}_system_prompt(state: DebateState) -> str:
    """Role definition, behavioral rules, output format instructions."""

def build_{role}_user_message(state: DebateState) -> str:
    """Question + context + debate history + moderator guidance."""
```

## System Prompt Structure

1. **Role identity** — Who the agent is and their stance
2. **Behavioral rules** — Hard constraints (e.g., "must reference argument IDs")
3. **Output format** — Argument ID scheme, field expectations
4. **Confidence shift** — Explain what -1.0 to 1.0 range means
5. **Round-specific behavior** — Round 1 (independent) vs. later rounds (respond to rebuttals)

## User Message Structure

1. **Decision question** — `state.question`
2. **Additional context** — `state.context` (if provided)
3. **Debate history** — Formatted prior rounds via helper functions
4. **Moderator guidance** — `state.rounds[-1].moderator.guidance_for_next_round`
5. **Round indication** — Current round number

## Key Rules

1. **Language handling**: Check `state.config.language` — support `"zh"`, `"en"`, `"auto"` (auto-detect from question)
2. **Argument ID format**: `{ROLE}-R{round}-{index}` — Advocate uses `ADV-`, Critic uses `CRT-`
3. **Round awareness**: System prompts MUST differentiate Round 1 (build initial arguments) from Round 2+ (respond to rebuttals, make concessions)
4. **History formatting**: Use private helper functions (`_format_history()`, `_format_advocate_output()`, etc.) for consistent transcript construction
5. **Moderator guidance**: Always append if available — the Moderator's `guidance_for_next_round` steers focus
6. **Evidence requirement**: Prompts must require reasoning chains and evidence, not bare assertions

## Helper Functions

Common private helpers within prompt modules:
- `_format_history(state)` — Full round-by-round transcript
- `_format_advocate_output(response)` — Formatted advocate arguments
- `_format_current_round_arguments(state)` — Arguments from current round only
