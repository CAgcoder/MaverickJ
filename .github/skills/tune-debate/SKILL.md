---
name: tune-debate
description: "Tune and optimize debate quality: adjust convergence parameters, improve prompt effectiveness, configure per-agent models, reduce token costs, or improve argument depth. Use when debate output quality is poor, too shallow, too expensive, or needs domain-specific tuning."
argument-hint: "Describe what aspect to tune (e.g., reduce cost, improve depth, faster convergence)"
---
# Tune Debate Quality

## When to Use

- Debate produces shallow or repetitive arguments
- Debate is too expensive (token cost too high)
- Debate doesn't converge or converges too early
- Need to tune for a specific domain or question type

## Tuning Parameters

### 1. Convergence Tuning (`config.yaml`)

```yaml
debate:
  max_rounds: 5                          # Hard limit on rounds
  convergence_threshold: 2               # Consecutive high-score rounds needed
  convergence_score_target: 0.8          # 0-1, higher = harder to converge
  transcript_compression_after_round: 2  # Compress old rounds after this
```

| Goal | Adjustment |
|------|------------|
| Deeper debate | Increase `max_rounds` to 7-8, raise `convergence_score_target` to 0.85 |
| Faster convergence | Lower `convergence_score_target` to 0.7, lower `convergence_threshold` to 1 |
| Lower cost | Reduce `max_rounds` to 3, lower `transcript_compression_after_round` to 1 |

### 2. Model Selection

Per-agent model assignment in `config.yaml`:

```yaml
agents:
  advocate:
    provider: claude
    model: claude-sonnet-4-20250514    # Strong reasoning for arguments
    temperature: 0.7                    # Higher creativity
  critic:
    provider: claude
    model: claude-sonnet-4-20250514    # Strong reasoning for rebuttals
    temperature: 0.7
  fact_checker:
    provider: openai
    model: gpt-4o-mini                 # Cost-efficient for verification
    temperature: 0.3                    # Low temperature for accuracy
  moderator:
    provider: claude
    model: claude-haiku-4-5-20251001   # Fast, cost-efficient for summaries
    temperature: 0.5
  report_generator:
    provider: claude
    model: claude-sonnet-4-20250514    # High quality for final report
    temperature: 0.5
```

| Goal | Strategy |
|------|----------|
| Highest quality | Use strongest model (Sonnet/GPT-4o) for all agents |
| Cost-optimized | Use mini/Haiku for fact_checker and moderator |
| Speed-optimized | Use Flash/Haiku models across the board |

### 3. Temperature Tuning

| Role | Low (0.2-0.4) | Medium (0.5-0.7) | High (0.7-1.0) |
|------|----------------|-------------------|-----------------|
| Advocate | Conservative arguments | Balanced | Creative, bold claims |
| Critic | Focused rebuttals | Balanced | Wide-ranging challenges |
| Fact-Checker | Strict verification | — | Not recommended |
| Moderator | Predictable flow | Balanced | Not recommended |

### 4. Prompt Tuning

For domain-specific tuning, modify prompts in `maverickj/prompts/`:

- **Add domain context** to system prompts for specialized debates
- **Strengthen evidence requirements** by adding explicit instructions
- **Adjust concession sensitivity** — "concede more easily" vs. "defend strongly"
- **Guide argument depth** — "provide detailed technical analysis" vs. "focus on business impact"

### 5. Transcript Compression

`transcript_compression_after_round` controls when old rounds are summarized:
- **Lower value (1)**: Aggressive compression, lower cost, risk of losing context
- **Higher value (3-4)**: Full context preserved longer, higher cost, better continuity
- **Rule of thumb**: Set to `max_rounds / 2` for balanced cost/quality

## Cost Estimation

Approximate per-debate costs (3 rounds):
- **Budget**: ~$0.05-0.10 (mini/Haiku models)
- **Standard**: ~$0.30-0.50 (Sonnet/GPT-4o mix)
- **Premium**: ~$1.00-2.00 (Opus/GPT-4o all agents)

Check actual costs via `DebateMetadata.total_cost_usd` after each run.
