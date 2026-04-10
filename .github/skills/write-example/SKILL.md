---
name: write-example
description: "Create a new debate example script. Use when adding a new use case, demo scenario, or sample question for the debate engine. Covers the standard example pattern with config loading, question definition, and report saving."
argument-hint: "Describe the decision scenario (e.g., cloud migration, hiring strategy)"
---
# Write a Debate Example

## When to Use

- Creating a new example script in `examples/`
- Demonstrating a specific use case or industry scenario
- Building a template for users to customize

## Example Pattern

All examples follow this exact structure:

```python
"""
{Scenario Title}
{Brief description of the decision scenario}
"""

import asyncio

from maverickj.main import load_config, run_debate
from maverickj.output.renderer import render_report_to_markdown


async def main():
    # 1. Load configuration
    config = load_config("config.yaml")

    # 2. Define the decision question
    question = "Should we {specific decision}?"

    # 3. Provide context (optional but recommended)
    context = """
    - Key constraint 1
    - Key constraint 2
    - Current situation description
    - Relevant metrics or data points
    """

    # 4. Run the debate
    final_state = await run_debate(question, config, context)

    # 5. Render and save report
    if final_state.final_report:
        markdown = render_report_to_markdown(
            final_state.final_report, final_state
        )
        output_file = "{scenario_name}-report.md"
        with open(output_file, "w") as f:
            f.write(markdown)
        print(f"Report saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Guidelines

1. **Question format**: Phrase as a clear yes/no or A-vs-B decision
2. **Context quality**: Include concrete constraints, team size, timelines, budget — more context → better debate
3. **Output filename**: Use kebab-case matching the scenario: `{scenario}-report.md`
4. **Docstring**: Include scenario title and brief description at file top

## Existing Examples

Reference these for patterns:
- `examples/build_vs_buy.py` — Build vs. buy technology decision
- `examples/java_to_go.py` — Programming language migration decision
