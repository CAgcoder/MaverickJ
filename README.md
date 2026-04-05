# 🏛️ Auto-Gangjing — 多 Agent 辩论式决策引擎

> 自动化杠精，对抗赛博精神病

[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![Claude API](https://img.shields.io/badge/LLM-Claude%20Sonnet-orange.svg)](https://www.anthropic.com/)
[![License: ISC](https://img.shields.io/badge/License-ISC-green.svg)](LICENSE)

---

## 目录

- [项目简介](#项目简介)
- [核心价值](#核心价值)
- [系统架构](#系统架构)
- [关键功能与实现细节](#关键功能与实现细节)
  - [1. 四 Agent 协作辩论系统](#1-四-agent-协作辩论系统)
  - [2. 编排引擎 (Orchestrator)](#2-编排引擎-orchestrator)
  - [3. 论点注册与生命周期追踪](#3-论点注册与生命周期追踪)
  - [4. LLM 调用层与结构化输出](#4-llm-调用层与结构化输出)
  - [5. 多轮收敛判定机制](#5-多轮收敛判定机制)
  - [6. 决策报告生成](#6-决策报告生成)
  - [7. CLI 实时辩论流](#7-cli-实时辩论流)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用方式](#使用方式)
- [输出效果](#输出效果)
- [依赖说明](#依赖说明)
- [测试](#测试)
- [成本估算](#成本估算)

---

## 项目简介

Auto-Gangjing 是一个基于多 Agent 协作的辩论式决策分析引擎。用户输入一个商业决策问题后，系统会启动 **4 个具有不同角色定位的 AI Agent**，通过多轮结构化辩论（正方论证 → 反方反驳 → 事实校验 → 主持人裁决），模拟真实的决策审议过程，最终输出一份包含正反论点、关键分歧、风险评估和行动建议的 **结构化决策报告**。

整个系统采用纯 TypeScript 实现，零框架依赖（不依赖 LangChain 等），通过 Anthropic Claude API 驱动 Agent 的推理与对话。

---

## 核心价值

**这不是简单的 pros/cons 列表。** 传统的 AI 问答只能给出单视角的分析，而本项目通过以下机制产出经过"压力测试"的高质量决策分析：

| 机制 | 说明 |
|------|------|
| 🔄 **动态对抗** | Critic 必须引用 Advocate 的具体论点 ID 进行反驳，而非"各说各话" |
| 📎 **证据引用** | 每个论点要求提供推理链和证据支撑，而非空泛断言 |
| 🤝 **立场修正** | Agent 必须诚实回应有效反驳，承认让步或修正论点 |
| ✅ **事实校验** | 中立的 Fact-Checker 审查双方论证的逻辑谬误和推理缺陷 |
| 📊 **收敛判定** | Moderator 实时计算收敛分数，在恰当时机终止辩论 |
| 📈 **论点生命周期** | 追踪每个论点从提出到存活/被推翻的完整历程 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户界面层                          │
│         CLI 交互式输入 → 实时辩论流输出 → 决策报告         │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 Orchestrator 编排层                      │
│                                                         │
│  ┌────────────┐   回合调度 / 状态管理 / 收敛判定          │
│  │ Moderator  │ ◄──────────────────────────────────┐    │
│  │   Agent    │   控制发言顺序、判断收敛、终止辩论    │    │
│  └─────┬──────┘                                    │    │
│        │ 指令                                      │    │
│  ┌─────▼──────┐  ┌────────────┐  ┌──────────────┐ │    │
│  │ Advocate   │  │  Critic    │  │ Fact-Checker │ │    │
│  │   Agent    │◄►│   Agent    │  │    Agent     │ │    │
│  │ (正方论证)  │  │ (反方反驳)  │  │ (逻辑校验)   │ │    │
│  └────────────┘  └────────────┘  └──────────────┘ │    │
│        │               │               │          │    │
│        └───────────────┴───────────────┘          │    │
│              ArgumentRegistry 论点注册表    ────────┘    │
│              TranscriptManager 辩论记录                  │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                     LLM 调用层                           │
│     Anthropic Claude API / Zod Schema 校验 / 重试机制     │
└─────────────────────────────────────────────────────────┘
```

**数据流（单回合）：**

```
用户问题 + 历史记录
      │
      ▼
Step 1: Advocate 发言 ──→ 提出/修正正方论点 + 反驳对方
      │
      ▼
Step 2: Critic 发言 ────→ 反驳正方论点 + 提出反方论点
      │
      ▼
Step 3: Fact-Checker ──→ 校验双方论点的逻辑/事实准确性
      │
      ▼
Step 4: Moderator ─────→ 总结本轮 + 计算收敛 + 决定是否继续
      │
      ├── shouldContinue=true  → 进入下一轮
      └── shouldContinue=false → 生成决策报告
```

---

## 关键功能与实现细节

### 1. 四 Agent 协作辩论系统

系统包含 4 个角色明确的 AI Agent，每个 Agent 都继承自同一个 `BaseAgent<T>` 抽象基类，通过泛型保证输入输出的类型安全。

#### Advocate Agent（正方论证者）

- **角色：** 资深商业战略顾问，负责构建最强的正方论证（"应该做"的方向）
- **行为规则：**
  - 第一轮独立提出 3-5 个核心正方论点，每个论点包含 `claim`（主张）、`reasoning`（推理过程）、`evidence`（支撑证据）
  - 后续轮次需回应 Critic 的反驳和 Fact-Checker 的校验结果
  - 对被有效反驳的论点执行让步（concessions）或修正（status: modified）
  - 对 Critic 的论点提出反驳（rebuttals），必须引用对方论点 ID（`targetArgumentId`）
  - 禁止无视有效反驳、禁止重复已被推翻的论点
- **论点 ID 格式：** `ADV-R{轮次}-{序号}`，如 `ADV-R1-01`
- **实现文件：** `src/agents/advocate.ts` + `src/prompts/advocate.prompt.ts`

#### Critic Agent（反方批评者）

- **角色：** 严苛的风险分析师，系统性挑战正方论点
- **行为规则：**
  - 逐条审视 Advocate 论点，找出逻辑漏洞、隐含假设、缺失考量
  - 对每个需反驳的论点产出 `Rebuttal`，必须引用具体论点 ID
  - 同时提出独立的反方论点
  - 只有当正方论点确实无懈可击时才承认让步
  - 禁止诡辩和稻草人谬误，必须攻击对方的真实论点
- **论点 ID 格式：** `CRT-R{轮次}-{序号}`，如 `CRT-R1-01`
- **实现文件：** `src/agents/critic.ts` + `src/prompts/critic.prompt.ts`

#### Fact-Checker Agent（事实校验者）

- **角色：** 逻辑学教授，中立第三方
- **行为规则：**
  - 对本轮所有 `active` 状态的论点和反驳进行校验
  - 判定结果分四类：
    - `valid` — 逻辑自洽、推理合理
    - `flawed` — 存在逻辑谬误或推理错误（需指出具体谬误类型）
    - `needs_context` — 论点合理但缺少关键上下文
    - `unverifiable` — 无法在当前信息下判断对错
  - 如发现认知偏误（确认偏误、幸存者偏误等），明确指出
  - 不选边站，只评估论证质量
- **实现文件：** `src/agents/factChecker.ts` + `src/prompts/factChecker.prompt.ts`

#### Moderator Agent（主持人 / 收敛控制器）

- **角色：** 辩论主持人，控制节奏、判断收敛、引导焦点
- **行为规则：**
  - 每轮总结辩论进展（`roundSummary`）
  - 识别当前关键未解决分歧（`keyDivergences`）
  - 计算收敛分数（`convergenceScore`，0-1）
  - 决定是否继续辩论（`shouldContinue`）
  - 给出下一轮焦点引导（`guidanceForNextRound`）
- **实现文件：** `src/agents/moderator.ts` + `src/prompts/moderator.prompt.ts`

#### Agent 基类设计

所有 Agent 继承自 `BaseAgent<T>` 抽象类（`src/agents/base.ts`），统一实现：

```typescript
abstract class BaseAgent<T> {
  protected abstract readonly role: string;
  protected abstract readonly schema: z.ZodType<T>;           // Zod 校验 schema
  protected abstract buildSystemPrompt(input: AgentInput): string;  // System Prompt 构造
  protected abstract buildUserMessage(input: AgentInput): string;   // User Message 构造

  async execute(input: AgentInput): Promise<{ result: T; metrics: AgentCallMetrics }>
}
```

`execute()` 方法内置 **JSON 解析失败自动重试**：当 LLM 输出无法解析为合法 JSON 时，会自动追加一条纠错消息要求 LLM 重新格式化，最多重试 2 次。

---

### 2. 编排引擎 (Orchestrator)

核心编排逻辑位于 `src/orchestrator/engine.ts` 中的 `runDebate()` 函数。

**主循环流程：**

```typescript
for (let round = 1; round <= config.maxRounds; round++) {
  // Step 1: Advocate 发言 → 注册论点到 ArgumentRegistry
  // Step 2: Critic 发言（接收本轮 Advocate 输出）→ 注册论点
  // Step 3: Fact-Checker 校验（接收双方输出）→ 标记 flawed 论点
  // Step 4: Moderator 裁决（接收全部输出）→ 判断是否收敛

  // 终止条件判定（三重保障）：
  // 1. Moderator 判定 shouldContinue = false
  // 2. convergenceScore >= 0.8 且连续 N 轮无新论点
  // 3. 达到最大轮数
}

// 辩论结束 → 生成决策报告
```

**回调系统（DebateCallbacks）：** 编排引擎通过回调机制将辩论过程暴露给外部，支持：

| 回调 | 触发时机 |
|------|---------|
| `onRoundStart(round)` | 每轮开始 |
| `onAgentStart(agent, round)` | 每个 Agent 开始执行 |
| `onAgentComplete(agent, round, result)` | 每个 Agent 完成执行 |
| `onRoundComplete(round)` | 每轮结束 |
| `onDebateEnd(state)` | 辩论终止 |

CLI 界面通过注册这些回调实现实时辩论流输出。

---

### 3. 论点注册与生命周期追踪

`ArgumentRegistry`（`src/orchestrator/argumentRegistry.ts`）是全局论点追踪器，维护每个论点从提出到最终状态的完整生命周期。

**核心数据结构：**

```typescript
interface TrackedArgument {
  argument: Argument;               // 论点内容
  raisedInRound: number;            // 在哪一轮提出
  raisedBy: "advocate" | "critic";  // 由谁提出
  rebuttals: Rebuttal[];            // 收到的所有反驳
  factChecks: FactCheck[];          // 收到的所有事实校验
}
```

**论点状态流转：**

```
active ──→ modified（被部分反驳后修正）
  │
  ├──→ rebutted（被有效反驳或 Fact-Checker 判定 flawed）
  │
  └──→ conceded（持有者主动承认让步）
```

**关键方法：**

| 方法 | 功能 |
|------|------|
| `register(arg, round, agent)` | 注册新论点 |
| `addRebuttal(targetId, rebuttal)` | 记录对论点的反驳 |
| `addFactCheck(targetId, check)` | 记录事实校验结果，flawed 自动标记为 rebutted |
| `getActiveArguments()` | 获取所有存活论点（active + modified） |
| `getActiveByAgent(agent)` | 按 Agent 过滤存活论点 |
| `getSurvivorStats()` | 获取论点存活统计 |
| `getChallengeCount(argId)` | 获取论点被挑战次数 |

---

### 4. LLM 调用层与结构化输出

#### 统一 LLM 客户端（`src/llm/client.ts`）

- 基于 `@anthropic-ai/sdk` 封装统一调用接口
- **单例模式：** 全局共享一个 `Anthropic` 客户端实例
- **自动重试：** 网络/API 错误自动重试最多 2 次，采用递增延迟（1s, 2s）
- **Token 统计：** 每次调用返回 `inputTokens` 和 `outputTokens`，由 Orchestrator 累加

```typescript
callLLM(systemPrompt, messages, model, temperature, maxTokens?) → LLMCallResult
```

#### 响应解析与校验（`src/llm/responseParser.ts`）

LLM 输出不可信任，系统通过以下机制保证输出合法：

1. **JSON 提取（`extractJSON`）：** 从 LLM 响应中提取 JSON，支持：
   - 标准 JSON 输出
   - markdown 代码块包裹的 JSON（` ```json ... ``` `）
   - 混杂说明文字的 JSON（正则提取）

2. **Zod Schema 校验（`parseResponse`）：** 对提取的 JSON 进行严格的结构化校验。每种 Agent 输出都定义了对应的 Zod Schema：

| Schema | 校验内容 |
|--------|---------|
| `AgentResponseSchema` | Advocate / Critic 的输出（论点、反驳、让步、信心变化） |
| `FactCheckResponseSchema` | Fact-Checker 的校验结果 |
| `ModeratorResponseSchema` | Moderator 的裁决（收敛分数、是否继续等） |
| `DecisionReportSchema` | 最终决策报告 |

所有 Schema 都包含类型约束、枚举限制和数值范围校验（如 `confidenceShift` 限制在 [-1, 1]，`convergenceScore` 限制在 [0, 1]，`strength` 限制在 [1, 10]）。

---

### 5. 多轮收敛判定机制

辩论不会无限进行，系统实现了**三重收敛保障**：

| 终止条件 | 判定逻辑 | 优先级 |
|---------|---------|--------|
| **Moderator 主动终止** | Moderator 在 prompt 中被指导计算收敛分数，当分数 ≥ 0.8 且辩论趋于稳定时设置 `shouldContinue = false` | 最高 |
| **Orchestrator 双重判定** | 当 `convergenceScore ≥ 0.8` **且** 连续 N 轮无实质性新论点（由 `convergenceThreshold` 配置）时终止 | 中 |
| **强制轮次上限** | 达到 `maxRounds` 后强制终止 | 兜底 |

**收敛分数计算依据（由 Moderator Agent 评估）：**
- 双方新论点数量是否递减
- 让步（concessions）是否增加
- 关键分歧是否在收窄
- 双方信心变化是否趋于 0

---

### 6. 决策报告生成

辩论终止后，系统调用一次独立的 LLM 请求生成结构化决策报告。

**报告内容包含：**

| 模块 | 说明 |
|------|------|
| **执行摘要** | 3-5 句话概括辩论结论 |
| **建议方向** | 包含方向、置信度（高/中/低）、前提条件 |
| **正方存活论点** | 按强度排序，包含经受挑战次数和修正历史 |
| **反方存活论点** | 同上 |
| **已解决分歧** | 辩论过程中双方达成共识的部分 |
| **未解决分歧** | 始终无法达成共识的核心问题 |
| **风险因素** | 关键风险提示 |
| **后续行动** | 基于未解决分歧建议的具体调研行动 |
| **辩论统计** | 总轮数、论点数、存活率、是否收敛 |

**Markdown 渲染（`src/output/reportRenderer.ts`）：** 将 JSON 格式的报告渲染为可读的 Markdown 文档，包含：
- 强度可视化条（`████████░░ 8/10`）
- 置信度色彩标记（🟢高/🟡中/🔴低）
- 执行时间和 Token 消耗统计

---

### 7. CLI 实时辩论流

`src/output/streamHandler.ts` 实现了终端彩色输出，通过 ANSI 转义码为不同 Agent 分配颜色：

| Agent | 颜色 | 图标 |
|-------|------|------|
| Advocate（正方） | 🟢 绿色 | 🟢 |
| Critic（反方） | 🔴 红色 | 🔴 |
| Fact-Checker | 🟡 黄色 | 🟡 |
| Moderator | 🔵 青色 | 🔵 |

实时展示内容：
- 每轮分隔线和轮次编号
- 每个 Agent 的论点、反驳、让步和信心变化
- Fact-Checker 的校验结果（✅/❌/⚠️/❓ 图标）
- Moderator 的收敛进度条
- 辩论结束原因

---

## 项目结构

```
debate-engine/
├── .env.example                         # 环境变量模板
├── .gitignore
├── package.json
├── tsconfig.json
├── vitest.config.ts                     # 测试配置
│
├── src/
│   ├── index.ts                         # CLI 入口（交互式/命令行参数）
│   ├── config.ts                        # 配置管理（读取 .env + 默认值）
│   │
│   ├── types/
│   │   ├── debate.ts                    # 全部核心类型定义
│   │   │   ├── DebateState              #   辩论全局状态
│   │   │   ├── DebateConfig             #   辩论配置
│   │   │   ├── DebateRound              #   单轮辩论数据
│   │   │   ├── AgentResponse            #   Agent 输出（论点/反驳/让步）
│   │   │   ├── Argument                 #   论点（含 ID、状态、推理链）
│   │   │   ├── Rebuttal                 #   反驳（引用目标论点 ID）
│   │   │   ├── FactCheck/Response       #   事实校验结果
│   │   │   ├── ModeratorResponse        #   主持人裁决
│   │   │   ├── DecisionReport           #   决策报告
│   │   │   └── AgentInput               #   Agent 统一输入
│   │   └── index.ts                     # 类型导出
│   │
│   ├── orchestrator/
│   │   ├── engine.ts                    # 主编排循环 runDebate()
│   │   ├── argumentRegistry.ts          # 论点注册、状态更新、存活统计
│   │   └── transcriptManager.ts         # 辩论记录管理
│   │
│   ├── agents/
│   │   ├── base.ts                      # Agent 抽象基类（LLM 调用+重试+解析）
│   │   ├── advocate.ts                  # 正方论证者
│   │   ├── critic.ts                    # 反方批评者
│   │   ├── factChecker.ts              # 事实校验者
│   │   └── moderator.ts                # 主持人
│   │
│   ├── prompts/
│   │   ├── advocate.prompt.ts           # Advocate System/User Prompt 模板
│   │   ├── critic.prompt.ts             # Critic Prompt 模板
│   │   ├── factChecker.prompt.ts        # Fact-Checker Prompt 模板
│   │   ├── moderator.prompt.ts          # Moderator Prompt 模板
│   │   └── reportGenerator.prompt.ts    # 报告生成 Prompt 模板
│   │
│   ├── llm/
│   │   ├── client.ts                    # Anthropic API 封装（单例+重试+Token 统计）
│   │   └── responseParser.ts            # JSON 提取 + Zod Schema 校验
│   │
│   └── output/
│       ├── reportRenderer.ts            # DecisionReport → Markdown 渲染
│       └── streamHandler.ts             # CLI 彩色实时输出
│
├── examples/
│   ├── java-to-go-migration.ts          # 示例：Java 服务迁移 Go
│   └── build-vs-buy.ts                  # 示例：自建 vs 采购分析平台
│
└── tests/
    ├── argumentRegistry.test.ts         # 论点注册器单元测试（6 用例）
    ├── responseParser.test.ts           # JSON 解析器单元测试（5 用例）
    ├── reportRenderer.test.ts           # 报告渲染器单元测试（2 用例）
    └── fixtures/
        ├── mockAdvocateResponse.json    # 模拟正方输出
        └── mockCriticResponse.json      # 模拟反方输出
```

---

## 快速开始

### 环境要求

- **Node.js** >= 18.0
- **npm** >= 9.0
- **Anthropic API Key**（[获取地址](https://console.anthropic.com/)）

### 1. 克隆项目

```bash
git clone https://github.com/CAgcoder/auto-gangjing.git
cd auto-gangjing/debate-engine
```

### 2. 安装依赖

```bash
npm install
```

### 3. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env` 文件，将 `ANTHROPIC_API_KEY` 替换为你的真实 API Key：

```env
ANTHROPIC_API_KEY=sk-ant-api03-你的真实key
```

### 4. 运行

```bash
# 交互模式（推荐）
npm start

# 直接传入决策问题
npm start -- "我们应该将 Java 服务迁移到 Go 吗？"

# 传入问题 + 补充背景
npm start -- "自建还是采购数据分析平台？" "团队15人，预算80万，6个月期限"
```

### 5. 运行示例

```bash
# Java 迁移 Go 决策分析
npx tsx examples/java-to-go-migration.ts

# 自建 vs 采购分析平台
npx tsx examples/build-vs-buy.ts
```

### 6. 运行测试

```bash
npm test
```

### 7. 构建

```bash
npm run build     # 编译 TypeScript → dist/
```

---

## 配置说明

所有配置通过 `.env` 文件管理，支持以下参数：

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | string | **必填** | Anthropic API Key |
| `MODEL_NAME` | string | `claude-sonnet-4-20250514` | 使用的 Claude 模型 |
| `TEMPERATURE` | number | `0.7` | 生成温度，越高越有创造性，越低越确定性 |
| `MAX_ROUNDS` | number | `5` | 最大辩论轮数（兜底限制） |
| `CONVERGENCE_THRESHOLD` | number | `2` | 连续多少轮无新论点视为收敛 |
| `LANGUAGE` | `zh` \| `en` | `zh` | 所有 Agent 输出的语言 |

---

## 使用方式

### 方式一：交互式 CLI

```bash
npm start
```

系统会提示你输入：
1. `🎯 请输入你的决策问题:` — 输入你的决策问题
2. `📋 补充背景（可选）:` — 输入相关背景信息，或直接回车跳过

### 方式二：命令行参数

```bash
npm start -- "决策问题" "可选的补充背景"
```

### 方式三：编程调用

```typescript
import { runDebate } from "./orchestrator/engine.js";
import { getDefaultConfig } from "./config.js";

const config = getDefaultConfig();
const state = await runDebate(
  "我们应该将 Java 服务迁移到 Go 吗？",
  config,
  "50 人后端团队，服务运行 3 年",
  {
    onRoundStart: (round) => console.log(`第 ${round} 轮开始`),
    onAgentComplete: (agent, round, result) => console.log(`${agent} 完成`),
  }
);

console.log(state.finalReport);  // DecisionReport 对象
```

### 输出文件

每次辩论结束后自动生成两个文件：

| 文件 | 格式 | 说明 |
|------|------|------|
| `debate-report-{id}.md` | Markdown | 可读的决策报告 |
| `debate-state-{id}.json` | JSON | 完整辩论数据（含所有轮次详情，可用于调试或二次分析） |

---

## 输出效果

### CLI 辩论流（实时）

```
╔══════════════════════════════════════════════════════════╗
║          🏛️  多 Agent 辩论式决策引擎                      ║
╚══════════════════════════════════════════════════════════╝

📌 决策问题: 我们应该将 Java 服务迁移到 Go 吗？
⚙️  配置: 最大 5 轮 | 模型 claude-sonnet-4-20250514 | 温度 0.7

════════════════════════════════════════════════════════════
  📢 第 1 轮辩论
════════════════════════════════════════════════════════════

🟢 正方论证者（Advocate）发言中...
  ── 正方论点 ──
  [ADV-R1-01] Go 的内存占用仅为 Java 的 1/10，显著降低部署成本
         Go 编译为原生二进制文件，无需 JVM...
  [ADV-R1-02] Go 的冷启动时间远优于 Java，适合 Serverless 架构
         ...

🔴 反方批评者（Critic）发言中...
  ── 反方论点 ──
  [CRT-R1-01] 迁移成本被严重低估，50人团队恢复生产力需12-18个月
         ...
  ── 反方反驳 ──
  ↩ ADV-R1-01: Java 21 虚拟线程和 GraalVM 已大幅改善资源消耗

🟡 事实校验者（Fact-Checker）校验中...
  ✅ ADV-R1-01: valid - 逻辑自洽...
  ⚠️ CRT-R1-01: needs_context - 缺少具体迁移案例数据...

🔵 主持人（Moderator）裁决中...
  📝 第一轮辩论展现了双方核心分歧...
  📊 收敛分数: [████████░░░░░░░░░░░░] 40%
  ➡️ 继续辩论
  🎯 下轮引导: 建议聚焦迁移成本的量化分析...
```

### 决策报告（Markdown）

最终报告包含完整的结构化分析：

```markdown
# 决策分析报告

## 执行摘要
经过 4 轮辩论...

## 建议
- **方向：** 建议采取渐进式迁移策略
- **置信度：** 🟡 中
- **前提条件：** ...

## 正方论点（支持方）
### 💪 Go 的冷启动优势对 Serverless 场景有决定性意义
- **强度：** ████████░░ 8/10
- **经受挑战：** 3 次

## 反方论点（反对方）
### ⚠️ 50人团队的迁移成本可能超过预算
- **强度：** ███████░░░ 7/10

## 未解决的核心分歧
- ❓ 迁移周期的预估存在根本性分歧...

## 辩论统计
| 项目 | 数值 |
|------|------|
| 总辩论轮数 | 4 |
| 提出论点总数 | 18 |
| 存活论点数 | 11 |
| 是否达成收敛 | 是 ✅ |
```

---

## 依赖说明

### 生产依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `@anthropic-ai/sdk` | ^0.82.0 | Anthropic Claude API 官方 SDK，用于调用 LLM |
| `zod` | ^4.3.6 | 运行时 Schema 校验库，用于验证 LLM 输出的 JSON 合法性 |
| `typescript` | ^6.0.2 | TypeScript 编译器 |
| `dotenv` | ^17.4.0 | 环境变量加载，从 `.env` 文件读取配置 |
| `uuid` | ^13.0.0 | UUID v4 生成器，用于辩论会话 ID |

### 开发依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `tsx` | ^4.21.0 | TypeScript 运行时，直接执行 `.ts` 文件（无需预编译） |
| `vitest` | ^4.1.2 | 单元测试框架，TypeScript 原生支持 |
| `@types/node` | ^25.5.2 | Node.js 类型定义 |
| `@types/uuid` | ^10.0.0 | uuid 库的类型定义 |

### 为什么不用 LangChain / LlamaIndex？

本项目的核心是 **编排逻辑**（4 Agent 的发言顺序、论点追踪、收敛判定）而非通用的 RAG 或 Chain 调用。引入框架会增加不必要的复杂度和抽象层，纯 TypeScript 实现让控制流更清晰、调试更直接。

---

## 测试

```bash
# 运行全部测试
npm test

# 监听模式
npm run test:watch
```

当前测试覆盖：

| 测试文件 | 测试用例数 | 覆盖模块 |
|---------|-----------|---------|
| `argumentRegistry.test.ts` | 6 | 论点注册、状态更新、反驳追踪、事实校验、存活统计 |
| `responseParser.test.ts` | 5 | JSON 提取（代码块/裸 JSON/混合文本） |
| `reportRenderer.test.ts` | 2 | Markdown 渲染正确性、统计数据 |

---

## 成本估算

基于 Claude Sonnet 模型，每次 Agent 调用约 3000 input tokens + 1500 output tokens：

| 项目 | 数值 |
|------|------|
| 每轮 LLM 调用 | 4 次（4 个 Agent） |
| 平均辩论轮数 | 3-5 轮 |
| 报告生成调用 | 1 次 |
| 总 LLM 调用 | ~17 次 |
| 总 Token 消耗 | ~76,500 tokens |
| **单次辩论成本** | **约 $0.30 - $0.50** |

---

## License

ISC
