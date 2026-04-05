# 多 Agent 辩论式决策引擎 — 项目实施计划

## 1. 项目概述

构建一个多 Agent 协作系统，用户输入商业决策问题后，系统启动 4 个专职 Agent 进行多轮结构化辩论，最终输出包含正反论点、关键分歧和建议的决策报告。

**核心价值：** 不是简单的 pros/cons 列表，而是通过 Agent 间的动态对抗、引用反驳、立场修正和事实校验，模拟真实的决策审议过程，产出经过压力测试的高质量决策分析。

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────┐
│                   用户界面层                      │
│         输入决策问题 → 实时辩论流 → 决策报告        │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Orchestrator 编排层                  │
│                                                  │
│  ┌──────────┐  回合调度 / 状态管理 / 收敛判定      │
│  │Moderator │◄─────────────────────────────────┐ │
│  │  Agent   │  控制发言顺序、判断是否收敛、终止辩论 │ │
│  └────┬─────┘                                  │ │
│       │ 指令                                    │ │
│  ┌────▼─────┐  ┌──────────┐  ┌──────────────┐ │ │
│  │Advocate  │  │ Critic   │  │ Fact-Checker │ │ │
│  │  Agent   │◄►│  Agent   │  │    Agent     │ │ │
│  │(正方论证) │  │(反方反驳) │  │(逻辑/事实校验)│ │ │
│  └──────────┘  └──────────┘  └──────────────┘ │ │
│       │              │              │          │ │
│       └──────────────┴──────────────┘          │ │
│                 共享辩论记录                      │ │
│              (Debate Transcript)               ──┘ │
└─────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│                  LLM 调用层                      │
│       统一的 API 客户端 / Prompt 模板管理          │
└─────────────────────────────────────────────────┘
```

---

## 3. 核心数据结构

### 3.1 辩论状态对象 `DebateState`

```typescript
interface DebateState {
  id: string;
  question: string;                    // 用户的决策问题
  context?: string;                    // 用户提供的补充背景
  config: DebateConfig;
  rounds: DebateRound[];               // 所有辩论回合
  status: "running" | "converged" | "max_rounds" | "error";
  convergenceReason?: string;          // 收敛原因
  finalReport?: DecisionReport;        // 最终决策报告
  metadata: {
    startedAt: string;
    completedAt?: string;
    totalLLMCalls: number;
    totalTokensUsed: number;
  };
}

interface DebateConfig {
  maxRounds: number;           // 最大辩论回合数，默认 5
  convergenceThreshold: number; // 连续多少回合无新论点视为收敛，默认 2
  model: string;               // LLM 模型标识
  temperature: number;         // 建议 0.7
  language: "zh" | "en";       // 输出语言
}
```

### 3.2 辩论回合 `DebateRound`

```typescript
interface DebateRound {
  roundNumber: number;
  phases: {
    advocate: AgentResponse;
    critic: AgentResponse;
    factCheck: FactCheckResponse;
    moderator: ModeratorResponse;
  };
}

interface AgentResponse {
  agentRole: string;
  arguments: Argument[];          // 本轮提出的论点
  rebuttals: Rebuttal[];          // 对对方论点的反驳
  concessions: string[];          // 承认对方有道理的部分
  confidenceShift: number;        // 本轮立场变化 [-1, 1]
}

interface Argument {
  id: string;                     // 如 "ADV-R1-01"
  claim: string;                  // 论点主张
  reasoning: string;              // 推理过程
  evidence?: string;              // 支撑证据
  status: "active" | "rebutted" | "conceded" | "modified";
}

interface Rebuttal {
  targetArgumentId: string;       // 反驳哪个论点
  counterClaim: string;
  reasoning: string;
}

interface FactCheckResponse {
  checks: FactCheck[];
  overallAssessment: string;
}

interface FactCheck {
  targetArgumentId: string;
  verdict: "valid" | "flawed" | "needs_context" | "unverifiable";
  explanation: string;
  correction?: string;
}

interface ModeratorResponse {
  roundSummary: string;            // 本轮总结
  keyDivergences: string[];        // 当前关键分歧
  convergenceScore: number;        // 0-1，越高越接近收敛
  shouldContinue: boolean;         // 是否继续辩论
  guidanceForNextRound?: string;   // 给下一轮的引导方向
}
```

### 3.3 决策报告 `DecisionReport`

```typescript
interface DecisionReport {
  question: string;
  executiveSummary: string;               // 一段话总结
  recommendation: {
    direction: string;                     // 建议方向
    confidence: "high" | "medium" | "low";
    conditions: string[];                  // 建议成立的前提条件
  };
  proArguments: ScoredArgument[];          // 正方存活论点（按强度排序）
  conArguments: ScoredArgument[];          // 反方存活论点
  resolvedDisagreements: string[];         // 辩论中已解决的分歧
  unresolvedDisagreements: string[];       // 仍存在的核心分歧
  riskFactors: string[];                  // 关键风险
  nextSteps: string[];                    // 建议的后续行动
  debateStats: {
    totalRounds: number;
    argumentsRaised: number;
    argumentsSurvived: number;
    convergenceAchieved: boolean;
  };
}

interface ScoredArgument {
  claim: string;
  strength: number;          // 1-10
  survivedChallenges: number; // 经历了多少次反驳仍然存活
  modifications: string[];   // 辩论中被修正的历史
}
```

---

## 4. Agent 设计详细规格

### 4.1 Advocate Agent（正方论证者）

**角色定位：** 为决策问题的正方（"应该做"）构建最强论证。

**System Prompt 要点：**
- 你是一位资深的商业战略顾问，负责论证正方立场
- 每轮必须产出结构化的 `Argument` 对象数组
- 第一轮：独立提出 3-5 个核心正方论点
- 后续轮次：你会收到 Critic 的反驳和 Fact-Checker 的校验结果
  - 对被有效反驳的论点：修正立场或承认让步（`concessions`）
  - 对被部分反驳的论点：补充论证、修正措辞
  - 引入新论点来强化正方整体论证
  - 对 Critic 的论点提出你自己的反驳（`rebuttals`）
- 每轮结束报告 `confidenceShift`：你对正方立场的信心变化
- 禁止无视对方有效反驳、禁止重复已被推翻的论点

**输入：** 决策问题 + 完整辩论记录（所有历史回合） + Moderator 的引导

**输出格式：** 严格按 `AgentResponse` JSON schema 输出

### 4.2 Critic Agent（反方批评者）

**角色定位：** 系统性地挑战正方论点，构建反方论证。

**System Prompt 要点：**
- 你是一位严苛的风险分析师，负责找出正方论证的漏洞
- 每轮工作流：
  1. 逐条审视 Advocate 的论点，找出逻辑漏洞、隐含假设、缺失考量
  2. 对每个需要反驳的论点产出 `Rebuttal`
  3. 提出自己独立的反方论点（`arguments`）
  4. 对 Advocate 的反驳做回应
- 如果 Advocate 的某个论点确实无懈可击，承认之（`concessions`）
- 反驳必须引用 Advocate 的具体论点 ID（`targetArgumentId`）
- 禁止诡辩、稻草人谬误；必须攻击对方的真实论点

**输入：** 决策问题 + 完整辩论记录 + 本轮 Advocate 的输出

**输出格式：** 严格按 `AgentResponse` JSON schema 输出

### 4.3 Fact-Checker Agent（事实校验者）

**角色定位：** 中立第三方，校验双方论据的逻辑一致性和事实准确性。

**System Prompt 要点：**
- 你是一位逻辑学教授，中立审视双方论证
- 对本轮所有 `active` 状态的论点和反驳进行校验：
  - `valid`：逻辑自洽、推理合理
  - `flawed`：存在逻辑谬误或推理错误（指出具体谬误类型）
  - `needs_context`：论点本身合理但缺少关键上下文才能成立
  - `unverifiable`：无法在当前信息下判断对错
- 如果发现某方使用了认知偏误（确认偏误、幸存者偏误等），明确指出
- 你不选边站，只评估论证质量

**输入：** 本轮 Advocate 和 Critic 的完整输出

**输出格式：** 严格按 `FactCheckResponse` JSON schema 输出

### 4.4 Moderator Agent（主持人 / 收敛控制器）

**角色定位：** 控制辩论节奏，判断收敛，引导焦点，生成最终报告。

**System Prompt 要点：**
- 你是辩论主持人，每轮结束后你需要：
  1. 总结本轮辩论进展（`roundSummary`）
  2. 识别当前最关键的未解决分歧（`keyDivergences`）
  3. 计算收敛分数（`convergenceScore`）：基于
     - 双方新论点数量是否递减
     - 让步（concessions）是否增加
     - 关键分歧是否在收窄
  4. 判断是否应该继续辩论（`shouldContinue`）
  5. 如果继续，给出下一轮的焦点引导（`guidanceForNextRound`）
- 收敛判定规则：
  - `convergenceScore >= 0.8` 且连续 2 轮无实质性新论点 → 终止
  - 达到 `maxRounds` → 强制终止
  - 双方信心变化趋于 0 → 终止

**输入：** 完整辩论记录 + 本轮所有 Agent 输出

**输出格式：** 严格按 `ModeratorResponse` JSON schema 输出 + 终止时输出 `DecisionReport`

---

## 5. 编排流程（Orchestrator）

### 5.1 单回合执行流

```
用户输入问题
    │
    ▼
┌─ Round N ──────────────────────────────────────┐
│                                                │
│  Step 1: Advocate 发言                          │
│    输入: question + history + moderator引导      │
│    输出: AgentResponse                          │
│    → 追加到 transcript                          │
│                                                │
│  Step 2: Critic 发言                            │
│    输入: question + history + 本轮advocate输出    │
│    输出: AgentResponse                          │
│    → 追加到 transcript                          │
│                                                │
│  Step 3: Fact-Checker 校验                      │
│    输入: 本轮 advocate + critic 输出              │
│    输出: FactCheckResponse                      │
│    → 标记被判定 flawed 的论点状态                  │
│                                                │
│  Step 4: Moderator 裁决                         │
│    输入: 完整 transcript + 本轮所有输出            │
│    输出: ModeratorResponse                      │
│    → 判断 shouldContinue                        │
│       - true  → 进入 Round N+1                  │
│       - false → 进入报告生成                     │
│                                                │
└────────────────────────────────────────────────┘
```

### 5.2 关键实现细节

**a) Transcript 管理**

每次调用 Agent 时，需要将完整的辩论历史作为上下文传入。为了控制 token 消耗：
- 前 2 轮：传完整 transcript
- 第 3 轮起：对历史轮次做摘要压缩，只保留当前轮和上一轮的完整内容
- 使用 Moderator 的 `roundSummary` 作为历史轮次的压缩替代

**b) 论点状态追踪**

维护一个全局的 `ArgumentRegistry`：

```typescript
class ArgumentRegistry {
  private arguments: Map<string, Argument & {
    raisedInRound: number;
    raisedBy: "advocate" | "critic";
    rebuttals: Rebuttal[];
    factChecks: FactCheck[];
  }>;

  // 注册新论点
  register(arg: Argument, round: number, agent: string): void;
  // 更新论点状态（被反驳/修正/让步）
  updateStatus(argId: string, status: Argument["status"]): void;
  // 获取所有存活论点
  getActiveArguments(): Argument[];
  // 获取论点的完整生命周期
  getArgumentHistory(argId: string): ArgumentLifecycle;
  // 生成论点存活统计
  getSurvivorStats(): SurvivorStats;
}
```

**c) 错误处理与重试**

- 单个 Agent 调用失败：重试 2 次，仍然失败则使用该 Agent 上一轮的输出 + 标记
- JSON 解析失败：要求 LLM 重新格式化（附带 schema 提示）
- 整轮失败：终止辩论，基于已有轮次生成部分报告

---

## 6. 报告生成逻辑

辩论终止后，由 Moderator Agent 执行最终报告生成调用：

**输入：** 完整 `DebateState`（包含所有轮次数据）

**Prompt 要点：**

```
基于以下完整的辩论记录，生成结构化决策报告。

要求：
1. executiveSummary：用 3-5 句话概括辩论结论
2. recommendation：给出建议方向、置信度、前提条件
   - 置信度基于：正方存活论点强度 vs 反方存活论点强度
   - 如果双方势均力敌，置信度为 "low"，建议 "需要更多信息"
3. proArguments / conArguments：
   - 只包含 status 为 "active" 或 "modified" 的论点
   - 按 strength 降序排列
   - strength 评分考虑：经受了多少次反驳仍存活、Fact-Checker 的评价
4. unresolvedDisagreements：标记辩论中始终无法达成共识的核心问题
5. nextSteps：基于 unresolvedDisagreements 建议具体的后续调研行动

严格按照 DecisionReport JSON schema 输出。
```

---

## 7. 文件结构

```
debate-engine/
├── README.md
├── package.json
├── tsconfig.json
├── .env.example                    # API keys 配置
│
├── src/
│   ├── index.ts                    # 入口：CLI 或 API server
│   ├── config.ts                   # 默认配置 & 环境变量
│   │
│   ├── types/
│   │   ├── debate.ts               # DebateState, DebateRound 等核心类型
│   │   ├── agents.ts               # AgentResponse, FactCheckResponse 等
│   │   └── report.ts               # DecisionReport 类型
│   │
│   ├── orchestrator/
│   │   ├── engine.ts               # 主编排循环：runDebate()
│   │   ├── argumentRegistry.ts     # 论点注册 & 状态追踪
│   │   └── transcriptManager.ts    # 辩论记录管理 & 压缩
│   │
│   ├── agents/
│   │   ├── base.ts                 # Agent 基类：LLM 调用、重试、JSON 解析
│   │   ├── advocate.ts             # Advocate Agent 实现
│   │   ├── critic.ts               # Critic Agent 实现
│   │   ├── factChecker.ts          # Fact-Checker Agent 实现
│   │   └── moderator.ts            # Moderator Agent 实现
│   │
│   ├── prompts/
│   │   ├── advocate.prompt.ts      # Advocate 的 system prompt 模板
│   │   ├── critic.prompt.ts        # Critic 的 system prompt 模板
│   │   ├── factChecker.prompt.ts   # Fact-Checker 的 system prompt 模板
│   │   ├── moderator.prompt.ts     # Moderator 的 system prompt 模板
│   │   └── reportGenerator.prompt.ts  # 报告生成 prompt
│   │
│   ├── llm/
│   │   ├── client.ts               # 统一 LLM 客户端（封装 API 调用）
│   │   └── responseParser.ts       # JSON 响应解析 & 校验
│   │
│   └── output/
│       ├── reportRenderer.ts       # 将 DecisionReport 渲染为 Markdown
│       └── streamHandler.ts        # 实时辩论过程的流式输出
│
├── prompts/                        # （可选）外置 prompt 文件
│   ├── advocate_system.md
│   ├── critic_system.md
│   ├── factchecker_system.md
│   └── moderator_system.md
│
├── examples/
│   ├── java-to-go-migration.ts     # 示例：Java 迁移 Go
│   └── build-vs-buy.ts             # 示例：自建 vs 采购
│
└── tests/
    ├── orchestrator.test.ts
    ├── agents/
    │   ├── advocate.test.ts
    │   ├── critic.test.ts
    │   ├── factChecker.test.ts
    │   └── moderator.test.ts
    ├── argumentRegistry.test.ts
    └── fixtures/                    # 模拟 LLM 响应的测试数据
        ├── mockAdvocateResponse.json
        └── mockCriticResponse.json
```

---

## 8. 实施步骤（分阶段）

### Phase 1：基础骨架（预计 2-3 天）

**目标：** 跑通最简单的单轮辩论

1. 初始化 TypeScript 项目，配置 tsconfig、eslint、依赖
2. 定义 `src/types/` 下所有核心类型
3. 实现 `src/llm/client.ts`：统一的 LLM 调用封装
   - 支持传入 system prompt + messages
   - 支持 JSON mode / structured output
   - 包含重试逻辑和 token 计数
4. 实现 `src/llm/responseParser.ts`：从 LLM 输出中提取合法 JSON
5. 实现 `src/agents/base.ts`：Agent 基类
   - `async execute(input: AgentInput): Promise<AgentResponse>`
   - 内含 prompt 组装、LLM 调用、响应解析
6. 实现 4 个 Agent 的最简版本（先硬编码 prompt，不做复杂的历史引用）
7. 实现 `src/orchestrator/engine.ts`：单轮编排（Advocate → Critic → FactChecker → Moderator）

**验证：** 输入一个决策问题，能输出一轮完整的 4 个 Agent 响应

### Phase 2：多轮辩论 & 收敛（预计 2-3 天）

**目标：** 实现真正的多轮动态辩论

1. 实现 `ArgumentRegistry`：论点注册、状态更新、查询
2. 实现 `TranscriptManager`：
   - 完整记录追加
   - 历史轮次摘要压缩（用 Moderator 的 roundSummary）
   - 为每个 Agent 构造合适的上下文窗口
3. 完善 Agent prompts：
   - Advocate/Critic：加入引用对方论点 ID 并反驳的指令
   - Moderator：加入收敛判定逻辑
4. 编排循环：`while (shouldContinue && round <= maxRounds)`
5. 实现收敛判定逻辑（在 Moderator 和 Orchestrator 双重判定）

**验证：** 一个决策问题能自动运行 3-5 轮并在适当时机收敛

### Phase 3：报告生成 & 输出（预计 1-2 天）

**目标：** 生成高质量的结构化决策报告

1. 实现报告生成 prompt 和调用逻辑
2. 实现 `reportRenderer.ts`：将 JSON 报告渲染为可读的 Markdown
3. 实现 `streamHandler.ts`：辩论过程的实时输出（供前端/CLI 使用）
4. 添加辩论统计信息到报告中

**验证：** 输出的 Markdown 报告包含完整结构且可读性好

### Phase 4：健壮性 & 优化（预计 2 天）

**目标：** 生产级可靠性

1. 完善错误处理：Agent 调用失败、JSON 解析失败、超时
2. Token 消耗优化：
   - 监控每轮 token 使用量
   - 动态调整 transcript 压缩策略
   - 设置总 token 预算上限
3. 添加配置文件支持（从 `.env` 或 YAML 读取）
4. 添加日志系统（每轮辩论过程可追溯）
5. 编写单元测试和集成测试

### Phase 5：交互界面（可选，预计 2-3 天）

**目标：** 提供可视化的辩论过程

选项 A — CLI 界面：
- 使用 `inquirer` 或 `ora` 做交互式命令行
- 实时显示每个 Agent 的发言
- 用颜色区分不同 Agent

选项 B — Web 界面：
- 简单的 React/Next.js 前端
- 左侧输入决策问题，右侧实时展示辩论流
- 最终报告可导出为 PDF/Markdown

---

## 9. 关键技术决策

| 决策项 | 推荐选择 | 理由 |
|--------|---------|------|
| 语言 | TypeScript | 类型安全对复杂数据结构至关重要 |
| LLM | Claude API (claude-sonnet-4-20250514) | 长上下文、结构化输出好、性价比高 |
| 框架依赖 | 无框架，纯 TypeScript | 这个项目的核心是编排逻辑，不需要 LangChain 等框架增加复杂度 |
| JSON 解析 | zod + 手动提取 | 用 zod schema 校验 LLM 输出的 JSON 合法性 |
| 并发 | 顺序执行 | Agent 间有依赖关系（Critic 依赖 Advocate），不适合并行 |
| 测试 | vitest | 快、TypeScript 原生支持 |

---

## 10. Prompt 工程注意事项

1. **强制 JSON 输出：** 每个 Agent 的 system prompt 末尾附带完整的 JSON schema，并明确要求"只输出 JSON，不要包含任何其他文字"

2. **论点 ID 引用机制：** Critic 反驳时必须引用 `targetArgumentId`，这是实现"动态对抗"而非"各说各话"的关键。Prompt 中需要反复强调这一点

3. **防止角色坍塌：** Advocate 不应该过早让步，Critic 不应该无脑反对。在 prompt 中加入"只有当对方论证确实无懈可击时才承认让步"

4. **Fact-Checker 中立性：** 明确告知"你不偏向任何一方，只评估论证质量"。如果发现两方论证质量差异大，如实报告

5. **Moderator 收敛判断：** 这是最难 prompt 的部分。需要在 prompt 中提供收敛判定的具体规则和示例，避免过早或过晚终止

6. **语言一致性：** 如果用户用中文提问，所有 Agent 的输出都应该是中文（在 system prompt 中指定）

---

## 11. 成本估算

基于 Claude Sonnet，假设每次 Agent 调用平均 3000 input tokens + 1500 output tokens：

| 项目 | 计算 |
|------|------|
| 每轮 LLM 调用 | 4 次（4 个 Agent） |
| 平均辩论轮数 | 4 轮 |
| 总 LLM 调用 | 16 次 + 1 次报告生成 = 17 次 |
| 总 tokens | ~76,500 tokens（含 input 增长） |
| 预估单次辩论成本 | 约 $0.30 - $0.50 |

注意：随着轮次增加，input tokens 会增长（因为要传入历史记录）。Transcript 压缩策略可有效控制这一增长。

---

## 12. 给 Copilot 的实施提示

- 请严格按照 Phase 1 → 5 的顺序实施，每个 Phase 完成后验证再继续
- `types/` 下的类型定义是全局契约，所有模块都围绕这些类型展开
- 每个 Agent 的实现模式高度一致（继承 base），区别仅在 prompt 和输入构造
- Orchestrator 是核心控制器，保持其逻辑清晰简洁，不要在里面塞业务逻辑
- Prompt 模板建议用 template literal 函数，方便动态注入上下文变量
- 所有 LLM 输出都要经过 zod schema 校验，不要信任原始输出