# 辩论执行协议

> 本文件定义辩论的状态结构、执行流程、收敛终止逻辑和论点 ID 规范。

---

## 1. 状态结构

辩论引擎维护一个全局 `DebateState`，在每个 Agent 节点间传递：

```
DebateState:
  question: str               # 决策问题
  context: str | null          # 补充背景
  current_round: int           # 当前轮次 (从 1 开始)
  max_rounds: int              # 最大轮数 (默认 5)
  convergence_score_target: float  # 收敛阈值 (默认 0.8)
  rounds: list[DebateRound]    # 历史轮次记录
  argument_registry: dict      # 论点生命周期注册表 (见 05-registry.md)
  status: "running" | "converged" | "max_rounds" | "error"
  convergence_reason: str | null
```

每个 `DebateRound` 包含:
```
DebateRound:
  round_number: int
  advocate: AgentResponse      # 正方输出
  critic: AgentResponse        # 反方输出
  fact_check: FactCheckResponse # 校验输出
  moderator: ModeratorResponse  # 裁决输出
```

---

## 2. 论点 ID 规范

```
格式: {ROLE_PREFIX}-R{round}-{index}

正方: ADV-R1-01, ADV-R1-02, ADV-R2-01, ...
反方: CRT-R1-01, CRT-R1-02, CRT-R2-01, ...
```

- `ROLE_PREFIX`: `ADV` (Advocate) 或 `CRT` (Critic)
- `R{round}`: 提出轮次
- `{index}`: 本轮内序号，从 01 开始

反驳 (Rebuttal) 通过 `target_argument_id` 引用对方论点 ID。

---

## 3. 论点生命周期

每个论点有 4 种状态，单向流转：

```
                    ┌── 被有效反驳 ──→ REBUTTED
                    │
  ACTIVE ──────────┼── 提出方让步 ──→ CONCEDED
                    │
                    └── 经修正继续 ──→ MODIFIED (仍存活)
```

- **ACTIVE**: 存活，未被有效反驳
- **REBUTTED**: 已被有效反驳 (Fact-Checker 判 flawed 也会触发)
- **CONCEDED**: 提出方主动承认对方有理
- **MODIFIED**: 经修正后继续存活 (计为存活)

---

## 4. 每轮执行顺序

```
┌─────────────────────────────────────────────────────┐
│                    单轮辩论流程                        │
│                                                     │
│  1. Round Setup — 递增轮次，清空当前轮临时数据          │
│       ↓                                             │
│  2. Advocate — 正方发言                               │
│     · 第 1 轮：提出 3-5 个核心论点                     │
│     · 第 2+ 轮：反驳 + 修正/让步 + 可选新论点           │
│       ↓                                             │
│  3. Critic — 反方发言                                 │
│     · 检查正方论点 → 反驳 + 提出反面论点               │
│     · 回应正方对自己论点的反驳                         │
│       ↓                                             │
│  4. Fact-Checker — 校验本轮所有论点和反驳              │
│     · 判定: valid / flawed / needs_context /         │
│       unverifiable                                  │
│     · flawed → 自动将论点标记为 REBUTTED              │
│       ↓                                             │
│  5. Moderator — 裁决                                  │
│     · 总结 → 识别分歧 → 算收敛分数 → 裁决继续/终止    │
│       ↓                                             │
│  6. 条件分支:                                         │
│     · should_continue = true → 回到步骤 1             │
│     · should_continue = false → 进入报告生成          │
└─────────────────────────────────────────────────────┘
```

---

## 5. 收敛终止条件

满足以下 **任一** 条件时终止辩论：

| 条件 | 说明 |
|------|------|
| 达到最大轮数 | `current_round >= max_rounds` |
| Moderator 判定终止 | `should_continue = false` |
| 连续高分 | 连续 2 轮 `convergence_score >= convergence_score_target` |
| 错误状态 | `status == "error"` |

终止后进入 **Report Generator** 阶段，生成最终 `DecisionReport`。

---

## 6. 报告生成

终止后，Report Generator 读取完整辩论 transcript，输出 `DecisionReport`：

- **executive_summary**: 3-5 句概括
- **recommendation**: 建议方向 + 置信度 (high/medium/low) + 前提条件
- **pro/con_arguments**: 仅包含 active/modified 状态的论点，按 strength 降序
- **unresolved_disagreements**: 未达成共识的核心议题
- **next_steps**: 具体可执行的后续行动 (不允许模糊措辞)

---

## 7. 执行伪代码

```python
async def run_adversarial_debate(question, context=None, max_rounds=5):
    state = init_state(question, context, max_rounds)

    while True:
        state.current_round += 1

        # 1. Advocate
        advocate_resp = await call_advocate(state)
        update_registry(state, advocate_resp, "advocate")

        # 2. Critic (sees Advocate's output)
        critic_resp = await call_critic(state, advocate_resp)
        update_registry(state, critic_resp, "critic")

        # 3. Fact-Checker (sees both)
        fact_check_resp = await call_fact_checker(state, advocate_resp, critic_resp)
        apply_fact_checks(state, fact_check_resp)

        # 4. Moderator (sees full transcript)
        moderator_resp = await call_moderator(state)
        state.rounds.append(DebateRound(advocate_resp, critic_resp, fact_check_resp, moderator_resp))

        # 5. Terminate?
        if should_terminate(state, moderator_resp):
            break

    # 6. Generate report
    return await call_report_generator(state)
```

---

## 8. Transcript 压缩策略

为控制上下文窗口长度：

| 轮次位置 | 传递内容 |
|----------|----------|
| ≤ `transcript_compression_after_round` (默认 2) | 完整 transcript |
| 更早的历史轮 | 仅 Moderator 的 `round_summary` (摘要代替全文) |
| 最近 1 轮 | 完整 transcript |
| 当前轮已完成阶段 | 完整输出 |

---

## 9. 错误处理与重试

```
LLM 调用:
  · 最多重试 2 次 (MAX_RETRIES = 2)
  · Pydantic 校验失败 → 附加格式纠正指令后重试
  · LLM API 错误 → 直接重试
  · 全部失败 → 抛出 RuntimeError

模型降级:
  · 每个 Agent 可配置 fallback 模型
  · 主模型失败时自动切换到 fallback
```
