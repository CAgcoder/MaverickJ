# 🏛️ 多 Agent 辩论式决策引擎

> 自动化杠精，对抗赛博精神病

通过 4 个 AI Agent 的多轮结构化辩论，对商业决策问题进行压力测试，产出经过正反论证的高质量决策分析报告。

## 核心特性

- **4 Agent 协作辩论**：正方论证者、反方批评者、事实校验者、主持人
- **多轮动态对抗**：Agent 间引用反驳、立场修正、让步承认
- **自动收敛判定**：主持人实时评估辩论收敛度，自动终止
- **结构化输出**：生成包含正反论点、分歧分析、风险提示的决策报告
- **实时辩论流**：CLI 彩色输出，实时展示每个 Agent 发言

## 架构

```
用户输入 → Orchestrator 编排循环
              │
    ┌─────────┼─────────────────┐
    │  Round N                   │
    │  1. Advocate (正方论证)     │
    │  2. Critic (反方反驳)       │
    │  3. Fact-Checker (事实校验) │
    │  4. Moderator (裁决/收敛)   │
    └────────────────────────────┘
              │
         决策报告 (Markdown)
```

## 快速开始

### 1. 安装依赖

```bash
cd debate-engine
npm install
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 Anthropic API Key
```

### 3. 运行

```bash
# 交互模式
npm start

# 直接传入问题
npm start -- "我们应该将 Java 服务迁移到 Go 吗？"

# 带补充背景
npm start -- "我们应该自建还是采购分析平台？" "团队15人，预算80万，6个月期限"
```

### 4. 运行示例

```bash
# Java 迁移 Go 示例
npx tsx examples/java-to-go-migration.ts

# 自建 vs 采购示例
npx tsx examples/build-vs-buy.ts
```

## 配置项

通过 `.env` 文件配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | - | Anthropic API Key（必填） |
| `MODEL_NAME` | `claude-sonnet-4-20250514` | 使用的模型 |
| `TEMPERATURE` | `0.7` | 生成温度 |
| `MAX_ROUNDS` | `5` | 最大辩论轮数 |
| `CONVERGENCE_THRESHOLD` | `2` | 连续几轮无新论点视为收敛 |
| `LANGUAGE` | `zh` | 输出语言（zh/en） |

## 项目结构

```
debate-engine/
├── src/
│   ├── index.ts                    # CLI 入口
│   ├── config.ts                   # 配置管理
│   ├── types/
│   │   └── debate.ts               # 核心类型定义
│   ├── orchestrator/
│   │   ├── engine.ts               # 主编排循环
│   │   ├── argumentRegistry.ts     # 论点状态追踪
│   │   └── transcriptManager.ts    # 辩论记录管理
│   ├── agents/
│   │   ├── base.ts                 # Agent 基类
│   │   ├── advocate.ts             # 正方论证者
│   │   ├── critic.ts               # 反方批评者
│   │   ├── factChecker.ts          # 事实校验者
│   │   └── moderator.ts            # 主持人
│   ├── prompts/                    # Prompt 模板
│   ├── llm/
│   │   ├── client.ts               # LLM API 客户端
│   │   └── responseParser.ts       # JSON 响应解析 & zod 校验
│   └── output/
│       ├── reportRenderer.ts       # Markdown 报告渲染
│       └── streamHandler.ts        # CLI 实时输出
├── examples/                       # 示例场景
├── tests/                          # 单元测试
└── .env.example                    # 环境变量模板
```

## 测试

```bash
npm test
```

## 输出示例

辩论过程中会实时展示每个 Agent 的发言，最终生成 Markdown 决策报告，包含：

- 执行摘要
- 推荐方向与置信度
- 正反存活论点（按强度排序）
- 已解决 / 未解决的分歧
- 关键风险因素
- 建议后续行动
- 辩论统计数据

## 技术栈

- **TypeScript** — 类型安全
- **Claude API** — LLM 调用
- **Zod** — 响应校验
- **Vitest** — 单元测试
- 无框架依赖，纯 TypeScript 实现
