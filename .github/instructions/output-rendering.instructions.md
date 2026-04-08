---
description: "Use when working with the output module: Rich console streaming, Markdown report rendering, or Jinja2 templates. Covers Rich panel patterns, agent styling, and template conventions."
applyTo: ["src/output/**", "src/templates/**"]
---
# Output & Rendering Patterns

## Module Structure

| File | Purpose |
|------|---------|
| `src/output/stream.py` | Rich console real-time debate output |
| `src/output/renderer.py` | DecisionReport → Markdown string |
| `src/templates/*.j2` | Jinja2 templates for reports and argument cards |

## Rich Console Streaming (`stream.py`)

- Global `Console` instance for styled output
- `AGENT_STYLES` dict maps agent roles to color/icon/label:
  - Advocate → green, Critic → red, Fact-Checker → blue, Moderator → yellow
- Functions: `print_debate_start()`, `print_round_start()`, `print_agent_start()`, `print_{role}_result()`, `print_debate_complete()`
- Uses Rich `Panel`, `Rule`, color-coded text, progress bars for convergence score

## Markdown Rendering (`renderer.py`)

```python
def render_report_to_markdown(report: DecisionReport, state: DebateState) -> str:
```

- Confidence mapping: HIGH → 🟢, MEDIUM → 🟡, LOW → 🔴
- Includes sections for: executive summary, pro/con arguments with scores, disagreements, risks, recommendations, debate stats

## Jinja2 Templates

Located in `src/templates/`:
- `report.md.j2` — Full decision report template
- `argument_card.md.j2` — Individual argument display card

Template variables come from `DecisionReport` and `DebateState` models.
