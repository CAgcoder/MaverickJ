# 论点注册表与评分

> 本文件定义论点注册表 (ArgumentRegistry) 的管理逻辑、生命周期跟踪和论点强度评分算法。

---

## 1. ArgumentRecord（论点记录）

注册表中每个论点存储为一条 `ArgumentRecord`:

```
ArgumentRecord:
  argument: Argument           # 论点本体 (id, claim, reasoning, evidence, status)
  raised_in_round: int         # 提出轮次
  raised_by: "advocate" | "critic"  # 提出方
  rebuttals: list[Rebuttal]    # 收到的反驳列表
  fact_checks: list[FactCheck] # 收到的校验结果列表
  modification_history: list[str]  # 修正历史记录
```

---

## 2. 注册表操作

### register(argument, round, agent)

注册新论点到注册表。

```
registry[arg.id] = ArgumentRecord(
    argument=arg,
    raised_in_round=round,
    raised_by=agent,
    rebuttals=[],
    fact_checks=[],
    modification_history=[]
)
```

### add_rebuttal(arg_id, rebuttal)

给目标论点追加一条反驳记录。

```
if arg_id in registry:
    registry[arg_id].rebuttals.append(rebuttal)
```

### add_fact_check(arg_id, check)

给目标论点追加校验结果。如果判定为 `flawed`，自动将论点状态标记为 `REBUTTED`。

```
if arg_id in registry:
    registry[arg_id].fact_checks.append(check)
    if check.verdict == "flawed":
        registry[arg_id].argument.status = "rebutted"
        registry[arg_id].modification_history.append(f"Fact-check: {check.explanation}")
```

### update_status(arg_id, new_status, reason)

手动更新论点状态（用于让步等场景）。

```
if arg_id in registry:
    registry[arg_id].argument.status = new_status
    if reason:
        registry[arg_id].modification_history.append(reason)
```

### get_active_arguments(side=None)

获取所有存活论点（状态为 `active` 或 `modified`），可按阵营过滤。

```
results = [r for r in registry.values() if r.argument.status in ("active", "modified")]
if side:
    results = [r for r in results if r.raised_by == side]
return results
```

---

## 3. 论点强度评分算法

生成最终报告时，对每个存活论点计算 `strength` 分数：

```
def calculate_strength(record: ArgumentRecord) -> int:
    score = 5                                    # 基础分

    # 每经受一次反驳挑战 +1 (存活说明论点有韧性)
    score += len(record.rebuttals)

    # Fact-Checker 评估加减分
    for fc in record.fact_checks:
        if fc.verdict == "valid":
            score += 1                           # 被认定有效 +1
        elif fc.verdict == "flawed":
            score -= 3                           # 被认定有缺陷 -3

    # 钳位到 [1, 10]
    return max(1, min(10, score))
```

**评分逻辑解读**:
- 基础 5 分，经受反驳越多说明论点越经得起考验
- Fact-Checker 的 `valid` 判定加 1 分，`flawed` 扣 3 分（重罚逻辑缺陷）
- `needs_context` 和 `unverifiable` 不影响分数

---

## 4. 存活统计

```
def get_survivor_stats(registry) -> dict:
    total = len(registry)
    active = count(r for r in registry.values() if r.status in ("active", "modified"))
    rebutted = count(r for r in registry.values() if r.status == "rebutted")
    conceded = count(r for r in registry.values() if r.status == "conceded")
    return {
        "total_raised": total,
        "survived": active,
        "rebutted": rebutted,
        "conceded": conceded,
    }
```

---

## 5. 各 Node 的注册表更新时机

| 执行阶段 | 注册表操作 |
|----------|-----------|
| Advocate Node | `register()` 新论点 + `add_rebuttal()` 正方反驳 + `update_status()` 让步 |
| Critic Node   | `register()` 新论点 + `add_rebuttal()` 反方反驳 + `update_status()` 让步 |
| Fact-Checker Node | `add_fact_check()` 所有校验结果 (flawed 自动触发 status 变更) |
| Moderator Node | 不修改注册表，仅读取 |
| Report Node   | 读取 `get_active_arguments()` + `calculate_strength()` 生成评分 |
