# 结构化输出 Schema

> 本文件定义所有 Agent 输入/输出的 JSON Schema，用于 LLM structured output 解析。

---

## 1. Argument（论点）

```json
{
  "type": "object",
  "required": ["id", "claim", "reasoning"],
  "properties": {
    "id": {
      "type": "string",
      "description": "论点 ID，格式如 ADV-R1-01 或 CRT-R1-01",
      "pattern": "^(ADV|CRT)-R\\d+-\\d+$"
    },
    "claim": {
      "type": "string",
      "description": "论点主张"
    },
    "reasoning": {
      "type": "string",
      "description": "推理过程"
    },
    "evidence": {
      "type": ["string", "null"],
      "description": "支撑证据 (可选)"
    },
    "status": {
      "type": "string",
      "enum": ["active", "rebutted", "conceded", "modified"],
      "default": "active",
      "description": "论点状态"
    }
  }
}
```

---

## 2. Rebuttal（反驳）

```json
{
  "type": "object",
  "required": ["target_argument_id", "counter_claim", "reasoning"],
  "properties": {
    "target_argument_id": {
      "type": "string",
      "description": "反驳目标论点 ID"
    },
    "counter_claim": {
      "type": "string",
      "description": "反驳主张"
    },
    "reasoning": {
      "type": "string",
      "description": "反驳推理"
    }
  }
}
```

---

## 3. FactCheck（事实校验）

```json
{
  "type": "object",
  "required": ["target_argument_id", "verdict", "explanation"],
  "properties": {
    "target_argument_id": {
      "type": "string",
      "description": "校验目标论点 ID"
    },
    "verdict": {
      "type": "string",
      "enum": ["valid", "flawed", "needs_context", "unverifiable"],
      "description": "校验判定"
    },
    "explanation": {
      "type": "string",
      "description": "校验说明"
    },
    "correction": {
      "type": ["string", "null"],
      "description": "修正建议 (可选)"
    },
    "fallacy_type": {
      "type": ["string", "null"],
      "description": "谬误类型 (可选，当 verdict=flawed 时应填写)"
    }
  }
}
```

---

## 4. AgentResponse（Advocate / Critic 输出）

```json
{
  "type": "object",
  "required": ["agent_role", "arguments"],
  "properties": {
    "agent_role": {
      "type": "string",
      "enum": ["advocate", "critic"],
      "description": "Agent 角色"
    },
    "arguments": {
      "type": "array",
      "items": { "$ref": "#/Argument" },
      "description": "本轮提出的论点"
    },
    "rebuttals": {
      "type": "array",
      "items": { "$ref": "#/Rebuttal" },
      "default": [],
      "description": "对对方论点的反驳"
    },
    "concessions": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "承认对方有道理的部分"
    },
    "confidence_shift": {
      "type": "number",
      "minimum": -1,
      "maximum": 1,
      "default": 0,
      "description": "本轮立场信心变化"
    }
  }
}
```

---

## 5. FactCheckResponse（Fact-Checker 输出）

```json
{
  "type": "object",
  "required": ["checks", "overall_assessment"],
  "properties": {
    "checks": {
      "type": "array",
      "items": { "$ref": "#/FactCheck" },
      "description": "所有校验结果"
    },
    "overall_assessment": {
      "type": "string",
      "description": "本轮论证质量整体评估"
    }
  }
}
```

---

## 6. ModeratorResponse（Moderator 输出）

```json
{
  "type": "object",
  "required": ["round_summary", "key_divergences", "convergence_score", "should_continue"],
  "properties": {
    "round_summary": {
      "type": "string",
      "description": "本轮总结"
    },
    "key_divergences": {
      "type": "array",
      "items": { "type": "string" },
      "description": "当前关键未解决分歧"
    },
    "convergence_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "收敛分数"
    },
    "should_continue": {
      "type": "boolean",
      "description": "是否继续辩论"
    },
    "guidance_for_next_round": {
      "type": ["string", "null"],
      "description": "下一轮焦点引导 (可选)"
    }
  }
}
```

---

## 7. DecisionReport（最终决策报告）

```json
{
  "type": "object",
  "required": ["question", "executive_summary", "recommendation", "pro_arguments", "con_arguments", "debate_stats"],
  "properties": {
    "question": {
      "type": "string",
      "description": "决策问题"
    },
    "executive_summary": {
      "type": "string",
      "description": "3-5 句概括"
    },
    "recommendation": {
      "type": "object",
      "required": ["direction", "confidence", "conditions"],
      "properties": {
        "direction": { "type": "string", "description": "建议方向" },
        "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
        "conditions": { "type": "array", "items": { "type": "string" }, "description": "建议成立的前提条件" }
      }
    },
    "pro_arguments": {
      "type": "array",
      "items": { "$ref": "#/ScoredArgument" },
      "description": "正方论点，按 strength 降序"
    },
    "con_arguments": {
      "type": "array",
      "items": { "$ref": "#/ScoredArgument" },
      "description": "反方论点，按 strength 降序"
    },
    "resolved_disagreements": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "已达成共识的议题"
    },
    "unresolved_disagreements": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "仍有分歧的议题"
    },
    "risk_factors": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "风险因素"
    },
    "next_steps": {
      "type": "array",
      "items": { "type": "string" },
      "default": [],
      "description": "具体后续行动"
    },
    "debate_stats": {
      "type": "object",
      "required": ["total_rounds", "arguments_raised", "arguments_survived", "convergence_achieved"],
      "properties": {
        "total_rounds": { "type": "integer" },
        "arguments_raised": { "type": "integer" },
        "arguments_survived": { "type": "integer" },
        "convergence_achieved": { "type": "boolean" },
        "total_tokens": { "type": "integer", "default": 0 },
        "total_cost_usd": { "type": "number", "default": 0 }
      }
    }
  }
}
```

### ScoredArgument（评分论点）

```json
{
  "type": "object",
  "required": ["claim", "strength", "survived_challenges"],
  "properties": {
    "claim": { "type": "string", "description": "论点主张" },
    "strength": { "type": "integer", "minimum": 1, "maximum": 10, "description": "论点强度" },
    "survived_challenges": { "type": "integer", "description": "经历挑战次数" },
    "modifications": { "type": "array", "items": { "type": "string" }, "default": [], "description": "修正历史" },
    "supporting_evidence": { "type": ["string", "null"], "description": "支撑证据" }
  }
}
```
