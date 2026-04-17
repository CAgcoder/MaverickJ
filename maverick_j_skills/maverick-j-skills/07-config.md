# 配置参数与使用示例

> 本文件包含运行参数配置、模型选择建议和实际使用示例。

---

## 1. 核心配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_rounds` | 5 | 最大辩论轮数。简单问题 3 轮够用，复杂决策可设 5-7 |
| `convergence_score_target` | 0.8 | 收敛分数阈值。越低越容易终止，越高辩论越深入 |
| `convergence_threshold` | 2 | 连续几轮达标才终止。防止单轮偶然高分导致过早结束 |
| `language` | auto | 输出语言。`auto` = 跟随问题语言，`zh` = 中文，`en` = 英文 |
| `transcript_compression_after_round` | 2 | 超过 N 轮后压缩历史 transcript，减少上下文消耗 |

---

## 2. 模型选择建议

### 按角色推荐

| 角色 | Temperature | 推荐特性 | 示例模型 |
|------|-------------|----------|----------|
| Advocate | 0.7 | 创造性推理、论证构建 | Claude Sonnet, GPT-4o |
| Critic | 0.7 | 批判性思维、漏洞识别 | Claude Sonnet, GPT-4o |
| Fact-Checker | 0.3 | 精确分析、逻辑判定 | GPT-4o-mini, Claude Haiku |
| Moderator | 0.5 | 平衡判断、收敛评估 | Claude Haiku, GPT-4o-mini |
| Report Gen | 0.5 | 结构化写作 | Claude Sonnet, GPT-4o |

### 成本优化策略

**全统一（低成本）**: 所有角色使用同一个快速模型
```yaml
default_provider: claude
default_model: claude-haiku-4-5-20251001
```

**混合配置（推荐）**: 关键角色用强模型，辅助角色用快模型
```yaml
agents:
  advocate:
    provider: claude
    model: claude-sonnet-4-20250514
    temperature: 0.7
  critic:
    provider: openai
    model: gpt-4o
    temperature: 0.7
  fact_checker:
    provider: openai
    model: gpt-4o-mini
    temperature: 0.3
  moderator:
    provider: claude
    model: claude-haiku-4-5-20251001
    temperature: 0.5
  report_generator:
    provider: claude
    model: claude-sonnet-4-20250514
    temperature: 0.5
```

### 成本参考

| 模型 | Input ($/1M tokens) | Output ($/1M tokens) | 3轮辩论估算 |
|------|---------------------|----------------------|-------------|
| Claude Haiku 4.5 | $0.80 | $4.00 | ~$0.05 |
| GPT-4o-mini | $0.15 | $0.60 | ~$0.02 |
| Claude Sonnet 4 | $3.00 | $15.00 | ~$0.20 |
| GPT-4o | $2.50 | $10.00 | ~$0.15 |

---

## 3. 使用示例

### 示例 1: 技术方案选型

```
问题: "我们应该将现有的 Java 后端服务迁移到 Go 吗？"

背景: "50 人后端团队，Java + Spring Boot 技术栈已运行 3 年。
痛点：
1. JVM 内存占用高，部署成本高
2. 冷启动慢，影响 Serverless 场景
3. 部分成员对 Go 感兴趣
4. 服务主要是 API Gateway 和微服务
5. 年收入约 700 万美元，技术预算约 110 万美元"

轮数: 3
```

### 示例 2: 商业决策

```
问题: "我们应该自建数据分析平台还是购买第三方方案？"

背景: "B2B SaaS 公司，200+ 企业客户，数据量 2TB/月，
当前使用 Mixpanel 年费 $180k，客户要求自定义仪表板和数据导出"

轮数: 5
```

### 示例 3: 团队管理

```
问题: "我们应该从部分远程办公转为全远程团队吗？"

背景: "120 人科技公司，当前每周 3 天到办公室。
旧金山办公室年租金 $900k。跨 3 个时区有 20% 的远程员工。"

轮数: 3
```

---

## 4. 快速触发模板

在 Claude Code / Cowork 中使用此格式触发辩论：

```
请对以下决策问题进行多 Agent 对抗式辩论分析：

问题: [你的决策问题]
背景: [可选的补充背景]
轮数: [可选，默认 3 轮]
语言: [可选，默认跟随问题语言]
```

---

## 5. 追问模式

第一轮辩论结束后，可以基于结论继续追问。追问时系统自动将上一轮结果注入为背景：

```
追问内容自动携带的背景:
  - 上一个辩题
  - 辩论结论概要
  - 建议方向和置信度
  - 主要正面论点 (top 3)
  - 主要反面论点 (top 3)
  - 尚未解决的分歧 (top 3)
```

示例追问：
```
基于上述辩论结果，如果决定迁移到 Go，最佳的渐进式迁移策略是什么？
```

---

## 6. 报告输出格式

最终报告为两段式 Markdown 文档：

```
# 决策分析报告

# 第一部分：完整辩论记录          ← 每轮 4 个 Agent 的完整对话
  ## 第 1 轮辩论
    ### 🟢 正方论证者               ← 论点 + 反驳 + 让步 + 信心变化
    ### 🔴 反方批评者
    ### 🔍 事实校验者               ← 每个论点的判定
    ### ⚖️ 主持人裁决               ← 总结 + 收敛分数条 + 裁决
  ## 第 2 轮辩论
  ...

# 第二部分：总结分析              ← LLM 生成的结构化分析
  ## 执行摘要
  ## 建议 (方向 + 置信度 + 前提)
  ## 正方论点 (按强度排序)
  ## 反方论点 (按强度排序)
  ## 已解决/未解决的分歧
  ## 风险因素
  ## 后续行动
  ## 辩论统计
```

---

## 7. 调优建议

| 症状 | 调整 |
|------|------|
| 辩论太浅，论点都很表面 | 增加 `max_rounds`，使用更强模型 (Sonnet/GPT-4o) |
| 辩论太贵 | 减少 `max_rounds`，Fact-Checker/Moderator 用轻量模型 |
| 收敛太快，讨论不充分 | 提高 `convergence_score_target` (如 0.85) |
| 不收敛，一直转圈 | 降低 `convergence_score_target`，检查 Moderator 提示词 |
| 论点重复 | 确保 Advocate/Critic 提示词中 "不得重复已被驳倒的论点" 生效 |
| 角色混淆 (单LLM模式) | 在每个角色切换时加强角色声明，用 `---` 分隔 |
