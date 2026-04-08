# 多 Agent 辩论式决策引擎 — 项目实施计划（Python 版）

## 1. 项目概述

构建一个多 Agent 协作系统，用户输入商业决策问题后，系统启动 4 个专职 Agent 进行多轮结构化辩论，最终输出包含正反论点、关键分歧和建议的决策报告。

**核心价值：** 通过 Agent 间的动态对抗、引用反驳、立场修正和事实校验，模拟真实的决策审议过程，产出经过压力测试的高质量决策分析。

---

## 2. 技术栈选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.12 | AI agent 生态主流，框架支持最好 |
| Agent 编排 | **LangGraph** | 原生支持有状态的多 Agent 循环图，天然适合"多轮辩论直到收敛"这种动态流程。比 LangChain 的 AgentExecutor 灵活得多——后者是线性链，LangGraph 是图，支持条件分支和循环 |
| LLM 抽象 | **LangChain Core** | 只用它的模型抽象层（`BaseChatModel`、`ChatPromptTemplate`），不用它的 Agent/Chain 上层封装。这样拿到多 provider 统一接口（Claude/OpenAI/Gemini 开箱即用），又不被框架绑死 |
| 数据校验 | **Pydantic v2** | LLM 输出的 JSON 校验、所有核心数据结构的定义。LangChain 本身就基于 Pydantic，无缝集成 |
| 结构化输出 | LangChain 的 `with_structured_output()` | 把 Pydantic model 直接传给 LLM 调用，自动处理各家模型的 JSON mode 差异（Claude 用 tool_use 模式、OpenAI 用 json_mode、Gemini 用 response_schema）。这解决了你之前担心的 JSON 输出一致性问题 |
| 配置管理 | **Pydantic Settings** | 从 YAML / 环境变量加载配置，带类型校验 |
| 测试 | **pytest** + pytest-asyncio | 标准选择 |
| 异步 | **asyncio** | LLM 调用天然是 IO 密集的，异步可以在未来支持并行评估 |

**为什么用 LangGraph 而不是纯手写编排：**

你之前 TS 版本里的 Orchestrator 本质上就是在手动实现一个状态机——"Advocate 发言 → Critic 发言 → FactChecker 校验 → Moderator 裁决 → 条件判断是否继续"。LangGraph 就是做这件事的专用工具。它给你的是：内置的状态管理（不用自己维护 `DebateState` 的传递）、可视化的执行图、checkpoint/resume（辩论可以中断恢复）、内置的流式输出。你把精力放在 Agent 逻辑和 prompt 上，而不是编排基础设施上。

**为什么还要用 LangChain Core：**

只用它的最底层——`ChatOpenAI`、`ChatAnthropic`、`ChatGoogleGenerativeAI` 这些模型封装。它们实现了统一的 `BaseChatModel` 接口，你的 Agent 代码调用 `model.invoke(messages)` 就行，底层是 Claude 还是 GPT 完全透明。不用 LangChain 的 Agent、Chain、Memory 等上层抽象，那些对你这个项目来说是过度封装。

---

## 3. 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                      用户界面层                            │
│           输入决策问题 → 实时辩论流 → 决策报告               │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                  LangGraph 状态图                          │
│                                                           │
│  ┌─────────┐    ┌─────────┐    ┌────────────┐            │
│  │Advocate │───►│ Critic  │───►│Fact-Checker│            │
│  │  Node   │    │  Node   │    │   Node     │            │
│  └─────────┘    └─────────┘    └─────┬──────┘            │
│       ▲                              │                    │
│       │         ┌────────────┐       │                    │
│       │         │ Moderator  │◄──────┘                    │
│       │         │   Node     │                            │
│       │         └─────┬──────┘                            │
│       │               │                                   │
│       │          should_continue()                        │
│       │           ╱          ╲                            │
│       └── True ──╱            ╲── False ──► report_node   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐     │
│  │              DebateState (共享状态)               │     │
│  │  question, config, rounds[], argument_registry,  │     │
│  │  status, convergence_score                       │     │
│  └─────────────────────────────────────────────────┘     │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│               LangChain Model 抽象层                       │
│                                                           │
│  ┌──────────────┐  ┌───────────┐  ┌──────────────┐       │
│  │ChatAnthropic │  │ ChatOpenAI│  │ChatGoogleGen │       │
│  │  (Claude)    │  │  (GPT)    │  │  (Gemini)    │       │
│  └──────────────┘  └───────────┘  └──────────────┘       │
│                                                           │
│              ModelRouter (配置驱动路由)                     │
└───────────────────────────────────────────────────────────┘
```

**LangGraph 的图结构具体定义：**

```
START → advocate_node → critic_node → fact_checker_node → moderator_node → should_continue
  ↑                                                                            │
  └──────────────────── continue (True) ◄──────────────────────────────────────┘
                                                                               │
                                                         terminate (False) ────▼
                                                                         report_node → END
```

这是一个带条件循环的有向图。LangGraph 的 `StateGraph` 原生支持这种结构，不需要你手动写 while 循环。

---

## 4. 核心数据结构（Pydantic Models）

### 4.1 辩论状态

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


class DebateStatus(str, Enum):
    RUNNING = "running"
    CONVERGED = "converged"
    MAX_ROUNDS = "max_rounds"
    ERROR = "error"


class DebateConfig(BaseModel):
    max_rounds: int = 5
    convergence_threshold: int = 2        # 连续几轮无新论点视为收敛
    convergence_score_target: float = 0.8  # convergenceScore 达到多少终止
    language: str = "auto"                 # "auto" = 跟随用户输入语言
    transcript_compression_after_round: int = 2  # 第几轮开始压缩历史


class DebateMetadata(BaseModel):
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_llm_calls: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0


class DebateState(BaseModel):
    """LangGraph 的共享状态对象，在所有 node 之间传递"""
    id: str
    question: str
    context: Optional[str] = None          # 用户补充的背景信息
    config: DebateConfig
    rounds: list["DebateRound"] = []
    argument_registry: dict[str, "ArgumentRecord"] = {}  # arg_id → 完整记录
    current_round: int = 0
    status: DebateStatus = DebateStatus.RUNNING
    convergence_reason: Optional[str] = None
    final_report: Optional["DecisionReport"] = None
    metadata: DebateMetadata
```

### 4.2 论点与反驳

```python
class ArgumentStatus(str, Enum):
    ACTIVE = "active"
    REBUTTED = "rebutted"
    CONCEDED = "conceded"
    MODIFIED = "modified"


class Argument(BaseModel):
    id: str                                # 如 "ADV-R1-01"
    claim: str                             # 论点主张
    reasoning: str                         # 推理过程
    evidence: Optional[str] = None         # 支撑证据
    status: ArgumentStatus = ArgumentStatus.ACTIVE


class Rebuttal(BaseModel):
    target_argument_id: str                # 反驳哪个论点
    counter_claim: str
    reasoning: str


class ArgumentRecord(BaseModel):
    """ArgumentRegistry 中存储的完整论点生命周期"""
    argument: Argument
    raised_in_round: int
    raised_by: str                         # "advocate" | "critic"
    rebuttals: list[Rebuttal] = []
    fact_checks: list["FactCheck"] = []
    modification_history: list[str] = []   # 每次修正的记录
```

### 4.3 Agent 响应

```python
class AgentResponse(BaseModel):
    """Advocate 和 Critic 的通用输出格式"""
    agent_role: str
    arguments: list[Argument]              # 本轮提出的论点
    rebuttals: list[Rebuttal] = []         # 对对方论点的反驳
    concessions: list[str] = []            # 承认对方有道理的部分
    confidence_shift: float = 0.0          # 本轮立场变化 [-1, 1]


class FactCheckVerdict(str, Enum):
    VALID = "valid"
    FLAWED = "flawed"
    NEEDS_CONTEXT = "needs_context"
    UNVERIFIABLE = "unverifiable"


class FactCheck(BaseModel):
    target_argument_id: str
    verdict: FactCheckVerdict
    explanation: str
    correction: Optional[str] = None
    fallacy_type: Optional[str] = None     # 如发现谬误，标注类型


class FactCheckResponse(BaseModel):
    checks: list[FactCheck]
    overall_assessment: str


class ModeratorResponse(BaseModel):
    round_summary: str
    key_divergences: list[str]             # 当前关键分歧
    convergence_score: float               # 0-1
    should_continue: bool
    guidance_for_next_round: Optional[str] = None
```

### 4.4 辩论回合

```python
class DebateRound(BaseModel):
    round_number: int
    advocate: AgentResponse
    critic: AgentResponse
    fact_check: FactCheckResponse
    moderator: ModeratorResponse
```

### 4.5 决策报告

```python
class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScoredArgument(BaseModel):
    claim: str
    strength: int                          # 1-10
    survived_challenges: int               # 经历多少次反驳仍存活
    modifications: list[str]               # 辩论中被修正的历史
    supporting_evidence: Optional[str] = None


class Recommendation(BaseModel):
    direction: str                         # 建议方向
    confidence: ConfidenceLevel
    conditions: list[str]                  # 建议成立的前提条件


class DebateStats(BaseModel):
    total_rounds: int
    arguments_raised: int
    arguments_survived: int
    convergence_achieved: bool
    total_tokens: int
    total_cost_usd: float


class DecisionReport(BaseModel):
    question: str
    executive_summary: str
    recommendation: Recommendation
    pro_arguments: list[ScoredArgument]    # 按 strength 降序
    con_arguments: list[ScoredArgument]    # 按 strength 降序
    resolved_disagreements: list[str]
    unresolved_disagreements: list[str]
    risk_factors: list[str]
    next_steps: list[str]
    debate_stats: DebateStats
```

### 4.6 模型路由配置

```python
class ModelAssignment(BaseModel):
    provider: str                          # "claude" | "openai" | "gemini" | "local"
    model: str                             # "claude-sonnet-4-20250514" | "gpt-4o" 等
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    fallback: Optional["ModelAssignment"] = None


class AgentModelConfig(BaseModel):
    advocate: ModelAssignment
    critic: ModelAssignment
    fact_checker: ModelAssignment
    moderator: ModelAssignment
    report_generator: ModelAssignment


class DebateEngineConfig(BaseModel):
    """顶层配置，从 YAML 加载"""
    default_provider: str = "claude"
    default_model: str = "claude-sonnet-4-20250514"
    default_temperature: float = 0.7
    agents: Optional[AgentModelConfig] = None  # 为空则所有 Agent 用 default
    debate: DebateConfig = DebateConfig()
```

---

## 5. Agent 设计详细规格

### 5.1 Advocate Agent（正方论证者）

**角色定位：** 为决策问题的正方（"应该做"）构建最强论证。

**System Prompt 关键指令：**
- 你是资深商业战略顾问，负责论证正方立场
- 第一轮：独立提出 3-5 个核心正方论点，每个论点必须包含 id（格式 ADV-R{轮次}-{序号}）、claim、reasoning
- 后续轮次：你会收到 Critic 的反驳和 Fact-Checker 的校验结果
  - 对被有效反驳（status 变为 rebutted）的论点：修正立场或承认让步
  - 对被部分反驳的论点：补充论证，将 status 改为 modified
  - 对 Critic 的论点提出反驳，必须引用 target_argument_id
  - 可引入新论点强化整体论证
- 每轮报告 confidence_shift：对正方立场的信心变化（-1 到 1）
- 禁止无视对方有效反驳、禁止重复已被推翻的论点

**输入构造：** question + transcript（压缩后）+ 上一轮 Moderator 的 guidance_for_next_round + ArgumentRegistry 中所有 active 状态论点的摘要

**输出：** 严格按 `AgentResponse` Pydantic schema（通过 `with_structured_output(AgentResponse)` 强制）

### 5.2 Critic Agent（反方批评者）

**角色定位：** 系统性挑战正方论点，构建反方论证。

**System Prompt 关键指令：**
- 你是严苛的风险分析师
- 逐条审视 Advocate 本轮论点，找出逻辑漏洞、隐含假设、缺失考量
- 每个反驳必须引用 target_argument_id（格式如 ADV-R1-01）
- 提出自己独立的反方论点（id 格式 CRT-R{轮次}-{序号}）
- 如果 Advocate 某个论点确实无懈可击，承认之（写入 concessions）
- 禁止诡辩、稻草人谬误；必须攻击对方的真实论点

**输入构造：** question + transcript + 本轮 Advocate 的完整输出

**输出：** 严格按 `AgentResponse` Pydantic schema

### 5.3 Fact-Checker Agent（事实校验者）

**角色定位：** 中立第三方，校验双方论据的逻辑一致性。

**System Prompt 关键指令：**
- 你是逻辑学教授，中立审视双方论证
- 对本轮所有 active 论点和反驳做校验，给出 verdict：
  - valid：逻辑自洽、推理合理
  - flawed：存在逻辑谬误（指出具体谬误类型，如确认偏误、幸存者偏误、滑坡谬误等）
  - needs_context：论点本身合理但缺少关键上下文
  - unverifiable：当前信息下无法判断
- 不选边站，只评估论证质量
- 如果发现某方使用了认知偏误，明确指出

**输入构造：** 本轮 Advocate 和 Critic 的完整输出（不需要历史 transcript，只看当轮）

**输出：** 严格按 `FactCheckResponse` Pydantic schema

### 5.4 Moderator Agent（主持人 / 收敛控制器）

**角色定位：** 控制辩论节奏，判断收敛，引导焦点。

**System Prompt 关键指令：**
- 你是辩论主持人，每轮结束后：
  1. 总结本轮辩论进展（round_summary）
  2. 识别当前最关键的未解决分歧（key_divergences）
  3. 计算 convergence_score（0-1），基于：
     - 双方新论点数量是否递减
     - concessions 是否增加
     - key_divergences 是否在收窄
     - 双方 confidence_shift 的绝对值是否趋于 0
  4. 判断 should_continue（基于收敛规则）
  5. 如果继续，给出下一轮焦点引导（聚焦哪个未解决分歧）
- 收敛判定：convergence_score >= 0.8 且连续 2 轮无实质性新论点 → False
- 给出的 round_summary 会被用作历史轮次的压缩替代，所以必须信息完整

**输入构造：** 完整 transcript + 本轮所有 Agent 输出 + ArgumentRegistry 统计信息

**输出：** 严格按 `ModeratorResponse` Pydantic schema

---

## 6. LangGraph 编排设计

### 6.1 状态图定义

```python
from langgraph.graph import StateGraph, END

# 定义图
workflow = StateGraph(DebateState)

# 添加节点
workflow.add_node("advocate", advocate_node)
workflow.add_node("critic", critic_node)
workflow.add_node("fact_checker", fact_checker_node)
workflow.add_node("moderator", moderator_node)
workflow.add_node("report", report_node)

# 定义边
workflow.set_entry_point("advocate")
workflow.add_edge("advocate", "critic")
workflow.add_edge("critic", "fact_checker")
workflow.add_edge("fact_checker", "moderator")

# 条件分支：继续辩论 or 生成报告
workflow.add_conditional_edges(
    "moderator",
    should_continue,       # 条件函数
    {
        "continue": "advocate",    # 回到 Advocate 开始新一轮
        "terminate": "report",     # 进入报告生成
    }
)
workflow.add_edge("report", END)

# 编译
app = workflow.compile()
```

### 6.2 每个 Node 的职责

每个 node 是一个函数，接收 `DebateState`，返回对 state 的更新：

```python
async def advocate_node(state: DebateState) -> dict:
    # 1. 从 state 构造上下文（transcript 压缩、active 论点摘要）
    # 2. 组装 prompt（system prompt + 上下文）
    # 3. 通过 ModelRouter 获取对应模型，调用 model.with_structured_output(AgentResponse)
    # 4. 解析响应，更新 ArgumentRegistry
    # 5. 返回 state 更新：新的 round 数据、更新后的 registry
    ...
```

### 6.3 Transcript 压缩策略

```python
class TranscriptManager:
    def build_context_for_agent(
        self,
        state: DebateState,
        agent_role: str,
        current_round: int,
    ) -> list[dict]:
        """为指定 Agent 构造合适的上下文"""
        messages = []

        if current_round <= state.config.transcript_compression_after_round:
            # 前 N 轮：传完整 transcript
            for round in state.rounds:
                messages.extend(self._round_to_messages(round))
        else:
            # 之后：历史轮次用 Moderator 的 round_summary 替代
            for round in state.rounds[:-1]:
                messages.append({
                    "role": "user",
                    "content": f"[第 {round.round_number} 轮摘要] {round.moderator.round_summary}"
                })
            # 最近一轮保留完整内容
            if state.rounds:
                messages.extend(self._round_to_messages(state.rounds[-1]))

        return messages
```

### 6.4 ArgumentRegistry

```python
class ArgumentRegistry:
    def __init__(self):
        self._arguments: dict[str, ArgumentRecord] = {}

    def register(self, arg: Argument, round_num: int, agent: str) -> None:
        """注册新论点"""
        self._arguments[arg.id] = ArgumentRecord(
            argument=arg,
            raised_in_round=round_num,
            raised_by=agent,
        )

    def update_status(self, arg_id: str, new_status: ArgumentStatus, reason: str = "") -> None:
        """更新论点状态"""
        if arg_id in self._arguments:
            record = self._arguments[arg_id]
            record.argument.status = new_status
            if reason:
                record.modification_history.append(reason)

    def add_rebuttal(self, arg_id: str, rebuttal: Rebuttal) -> None:
        """给论点添加反驳记录"""
        if arg_id in self._arguments:
            self._arguments[arg_id].rebuttals.append(rebuttal)

    def add_fact_check(self, arg_id: str, check: FactCheck) -> None:
        """给论点添加校验记录"""
        if arg_id in self._arguments:
            self._arguments[arg_id].fact_checks.append(check)
            if check.verdict == FactCheckVerdict.FLAWED:
                self.update_status(arg_id, ArgumentStatus.REBUTTED, f"Fact-check: {check.explanation}")

    def get_active_arguments(self, side: str = None) -> list[ArgumentRecord]:
        """获取所有存活论点，可按阵营过滤"""
        results = [r for r in self._arguments.values()
                   if r.argument.status in (ArgumentStatus.ACTIVE, ArgumentStatus.MODIFIED)]
        if side:
            results = [r for r in results if r.raised_by == side]
        return results

    def get_survivor_stats(self) -> dict:
        """生成论点存活统计"""
        total = len(self._arguments)
        active = len([r for r in self._arguments.values()
                      if r.argument.status in (ArgumentStatus.ACTIVE, ArgumentStatus.MODIFIED)])
        return {
            "total_raised": total,
            "survived": active,
            "rebutted": len([r for r in self._arguments.values()
                            if r.argument.status == ArgumentStatus.REBUTTED]),
            "conceded": len([r for r in self._arguments.values()
                            if r.argument.status == ArgumentStatus.CONCEDED]),
        }
```

### 6.5 收敛判定

```python
def should_continue(state: DebateState) -> str:
    """LangGraph 的条件边函数"""
    # 硬上限
    if state.current_round >= state.config.max_rounds:
        return "terminate"

    # 错误状态
    if state.status == DebateStatus.ERROR:
        return "terminate"

    # Moderator 判定
    latest = state.rounds[-1].moderator
    if not latest.should_continue:
        return "terminate"

    # 双重校验：即使 Moderator 说继续，如果 convergence_score 持续高位也终止
    recent_scores = [r.moderator.convergence_score for r in state.rounds[-2:]]
    if (len(recent_scores) >= 2
        and all(s >= state.config.convergence_score_target for s in recent_scores)):
        return "terminate"

    return "continue"
```

---

## 7. 多 Provider 路由层

### 7.1 利用 LangChain 的模型抽象

不需要自己写 Provider 接口了——LangChain 已经做了这件事。每个模型都实现了 `BaseChatModel`，调用方式统一。

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


def create_model(assignment: ModelAssignment) -> BaseChatModel:
    """根据配置创建对应的 LangChain 模型实例"""
    providers = {
        "claude": lambda a: ChatAnthropic(
            model=a.model,
            temperature=a.temperature or 0.7,
            max_tokens=a.max_tokens or 4096,
        ),
        "openai": lambda a: ChatOpenAI(
            model=a.model,
            temperature=a.temperature or 0.7,
            max_tokens=a.max_tokens or 4096,
        ),
        "gemini": lambda a: ChatGoogleGenerativeAI(
            model=a.model,
            temperature=a.temperature or 0.7,
            max_output_tokens=a.max_tokens or 4096,
        ),
    }
    return providers[a.provider](a)
```

### 7.2 ModelRouter

```python
class ModelRouter:
    def __init__(self, config: DebateEngineConfig):
        self.config = config
        self._models: dict[str, BaseChatModel] = {}
        self._init_models()

    def _init_models(self):
        if self.config.agents:
            # 混合调用模式：每个 Agent 单独配置
            for role in ["advocate", "critic", "fact_checker", "moderator", "report_generator"]:
                assignment = getattr(self.config.agents, role)
                self._models[role] = create_model(assignment)
        else:
            # 统一模式：所有 Agent 用同一个模型
            default = ModelAssignment(
                provider=self.config.default_provider,
                model=self.config.default_model,
                temperature=self.config.default_temperature,
            )
            for role in ["advocate", "critic", "fact_checker", "moderator", "report_generator"]:
                self._models[role] = create_model(default)

    def get_model(self, agent_role: str) -> BaseChatModel:
        return self._models[agent_role]

    def get_structured_model(self, agent_role: str, schema: type[BaseModel]) -> Runnable:
        """返回带结构化输出的模型，自动处理各家 JSON mode 差异"""
        model = self.get_model(agent_role)
        return model.with_structured_output(schema)
```

### 7.3 Fallback 机制

LangChain 有原生的 fallback 支持：

```python
from langchain_core.runnables import RunnableWithFallbacks

primary = ChatAnthropic(model="claude-sonnet-4-20250514")
fallback = ChatOpenAI(model="gpt-4o")

model_with_fallback = primary.with_fallbacks([fallback])
# 调用 primary 失败时自动切到 fallback
```

### 7.4 YAML 配置示例

```yaml
# config.yaml

# 方案 A：统一切换
default_provider: claude
default_model: claude-sonnet-4-20250514
default_temperature: 0.7

# 方案 B：混合调用（取消注释以启用）
# agents:
#   advocate:
#     provider: claude
#     model: claude-sonnet-4-20250514
#     temperature: 0.7
#   critic:
#     provider: openai
#     model: gpt-4o
#     temperature: 0.7
#   fact_checker:
#     provider: openai
#     model: gpt-4o-mini
#     temperature: 0.3
#   moderator:
#     provider: claude
#     model: claude-haiku-4-5-20251001
#     temperature: 0.5
#   report_generator:
#     provider: claude
#     model: claude-sonnet-4-20250514
#     temperature: 0.5

debate:
  max_rounds: 5
  convergence_threshold: 2
  convergence_score_target: 0.8
  language: auto
  transcript_compression_after_round: 2
```

---

## 8. 报告生成逻辑

报告生成是一个独立的 LangGraph node，在辩论终止后执行。

**输入：** 完整 `DebateState`（所有轮次 + ArgumentRegistry 统计）

**Prompt 关键指令：**
- 基于完整辩论记录生成决策报告
- executive_summary：3-5 句话概括
- recommendation.confidence 基于正方存活论点总强度 vs 反方存活论点总强度的比值。势均力敌则 "low"
- pro/con_arguments 只包含 active 或 modified 状态的论点，按 strength 降序
- strength 评分规则：基础分 5，每经受一次反驳仍存活 +1，Fact-Checker 评为 valid 额外 +1，评为 flawed 则 -3
- unresolved_disagreements：标记辩论中始终无法达成共识的问题
- next_steps：基于 unresolved_disagreements 建议具体后续调研行动，不允许"需要进一步研究"这种空话

**输出：** 通过 `with_structured_output(DecisionReport)` 强制结构化

**渲染：** 将 `DecisionReport` 渲染为 Markdown，使用 Jinja2 模板：

```
templates/
├── report.md.j2          # 完整报告模板
└── argument_card.md.j2   # 单个论点卡片模板（被 report 引用）
```

---

## 9. 项目文件结构

```
debate-engine/
├── README.md
├── pyproject.toml                      # 项目元信息 & 依赖（用 poetry 或 uv 管理）
├── config.yaml                         # 默认配置
├── .env.example                        # API keys
│
├── src/
│   ├── __init__.py
│   ├── main.py                         # 入口：CLI 启动辩论
│   │
│   ├── schemas/                        # Pydantic models（全局契约）
│   │   ├── __init__.py
│   │   ├── debate.py                   # DebateState, DebateRound, DebateConfig
│   │   ├── agents.py                   # AgentResponse, FactCheckResponse, ModeratorResponse
│   │   ├── arguments.py                # Argument, Rebuttal, FactCheck, ArgumentRecord
│   │   ├── report.py                   # DecisionReport, ScoredArgument, Recommendation
│   │   └── config.py                   # DebateEngineConfig, ModelAssignment, AgentModelConfig
│   │
│   ├── graph/                          # LangGraph 编排
│   │   ├── __init__.py
│   │   ├── builder.py                  # 构建 StateGraph，定义节点和边
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── advocate.py             # advocate_node 函数
│   │   │   ├── critic.py               # critic_node 函数
│   │   │   ├── fact_checker.py         # fact_checker_node 函数
│   │   │   ├── moderator.py            # moderator_node 函数
│   │   │   └── report.py              # report_node 函数
│   │   └── conditions.py              # should_continue 条件函数
│   │
│   ├── agents/                         # Agent 核心逻辑（被 nodes 调用）
│   │   ├── __init__.py
│   │   ├── base.py                     # Agent 基类：prompt 组装、模型调用、响应处理
│   │   ├── advocate.py
│   │   ├── critic.py
│   │   ├── fact_checker.py
│   │   └── moderator.py
│   │
│   ├── prompts/                        # Prompt 模板
│   │   ├── __init__.py
│   │   ├── advocate.py                 # Advocate 的 system prompt 构造函数
│   │   ├── critic.py
│   │   ├── fact_checker.py
│   │   ├── moderator.py
│   │   └── report_generator.py
│   │
│   ├── llm/                            # LLM 路由层
│   │   ├── __init__.py
│   │   ├── router.py                   # ModelRouter：按 agent role 路由到对应模型
│   │   ├── factory.py                  # create_model()：根据配置实例化 LangChain 模型
│   │   └── cost.py                     # 各模型定价表，计算 token 成本
│   │
│   ├── core/                           # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── argument_registry.py        # ArgumentRegistry 类
│   │   └── transcript_manager.py       # TranscriptManager 类
│   │
│   ├── output/                         # 输出层
│   │   ├── __init__.py
│   │   ├── renderer.py                 # DecisionReport → Markdown 渲染
│   │   └── stream.py                   # 实时辩论过程的流式输出
│   │
│   └── templates/                      # Jinja2 模板
│       ├── report.md.j2
│       └── argument_card.md.j2
│
├── examples/
│   ├── java_to_go.py                   # 示例：Java 迁移 Go
│   └── build_vs_buy.py                 # 示例：自建 vs 采购
│
└── tests/
    ├── conftest.py                     # pytest fixtures（mock 模型、测试配置）
    ├── test_graph/
    │   ├── test_builder.py
    │   └── test_conditions.py
    ├── test_agents/
    │   ├── test_advocate.py
    │   ├── test_critic.py
    │   ├── test_fact_checker.py
    │   └── test_moderator.py
    ├── test_core/
    │   ├── test_argument_registry.py
    │   └── test_transcript_manager.py
    └── fixtures/
        ├── mock_advocate_response.json
        ├── mock_critic_response.json
        └── sample_debate_state.json
```

---

## 10. 分阶段实施计划

### Phase 1：基础骨架（）

**目标：** 单轮辩论跑通

1. 初始化 Python 项目（）
2. 定义 `schemas/` 下所有 Pydantic models
3. 实现 `llm/factory.py` 和 `llm/router.py`（先只支持一个 provider）
4. 实现 4 个 Agent 的最简版本（`agents/` 下，硬编码 prompt，用 `with_structured_output` 强制输出格式）
5. 实现 LangGraph 的 `graph/builder.py`：构建单轮图（Advocate → Critic → FactChecker → Moderator → END，不循环）
6. 实现 `main.py` 入口

**验证：** 输入一个决策问题，能跑通一轮，4 个 Agent 各输出一个合法的 Pydantic 对象

### Phase 2：多 Provider 路由（）

**目标：** 支持统一切换和混合调用

1. 完善 `llm/factory.py`：支持 Claude、OpenAI、Gemini 三个 provider
2. 实现 YAML 配置加载（`schemas/config.py` + Pydantic Settings）
3. 实现 fallback 机制（`model.with_fallbacks()`）
4. 实现 `llm/cost.py`：按 provider 定价计算成本

**验证：** 用不同的 YAML 配置跑同一个问题，确认模型切换正常；故意断开一个 provider 的 API key，确认 fallback 生效

### Phase 3：多轮辩论 & 收敛（）

**目标：** 真正的多轮动态辩论

1. 实现 `core/argument_registry.py`：论点注册、状态更新、查询
2. 实现 `core/transcript_manager.py`：完整记录 + 历史压缩
3. 完善 Agent prompts：加入引用论点 ID 反驳的指令、让步规则
4. 在 LangGraph 图中加入条件循环边（`should_continue`）
5. 实现 `graph/conditions.py` 的收敛判定逻辑

**验证：** 一个决策问题能自动运行 3-5 轮并在适当时机收敛；检查 Critic 的 target_argument_id 是否真的引用了 Advocate 的论点

### Phase 4：报告生成 & 输出（）

**目标：** 高质量结构化决策报告

1. 实现 `graph/nodes/report.py`：报告生成 node
2. 实现 `output/renderer.py`：DecisionReport → Markdown（使用 Jinja2）
3. 实现 `output/stream.py`：辩论过程的实时流式输出（LangGraph 的 `.astream()` 原生支持）
4. 添加辩论统计到报告中

**验证：** 输出的 Markdown 报告结构完整、可读性好；流式输出能实时展示每个 Agent 的发言

### Phase 5：健壮性 & 优化（）

**目标：** 生产级可靠性

1. 完善错误处理：
   - 单个 Agent 调用失败：重试 2 次（LangChain 的 `model.with_retry()`），仍失败则用上一轮输出 + 标记
   - Pydantic 校验失败：自动重试一次并附带更严格的格式指令
   - 整轮失败：终止辩论，基于已有轮次生成部分报告
2. Token 消耗监控：通过 LangChain 的 callback 机制追踪每次调用的 token 用量
3. 日志系统：用 Python logging，每轮辩论过程可追溯
4. 编写测试：用 mock 模型测试图的执行流程、ArgumentRegistry、TranscriptManager

---

## 11. 关键技术决策

| 决策项 | 推荐选择 | 理由 |
|--------|---------|------|
| 编排框架 | LangGraph | 原生支持有状态循环图，比手写 while 循环更清晰，自带 checkpoint/streaming |
| 模型抽象 | LangChain Core 的 BaseChatModel | 多 provider 开箱即用，不用自己封装各家 API 差异 |
| 结构化输出 | `with_structured_output()` | 自动处理 Claude/OpenAI/Gemini 的 JSON mode 差异，直接返回 Pydantic 对象 |
| 数据校验 | Pydantic v2 | LangChain 原生支持，性能比 v1 快 5-50 倍 |
| 不用 LangChain 的 Agent | 是 | LangChain 的 AgentExecutor 是为 tool-calling agent 设计的，和你的"角色扮演辩论"模式不匹配。只用它的模型层 |
| 不用 LangChain 的 Memory | 是 | LangChain 的 Memory 模块是为聊天历史设计的，不适合你的 transcript 压缩策略。自己写 TranscriptManager 更灵活 |
| 包管理 | uv 或 poetry | uv 更快，poetry 更成熟，都行 |
| 异步 | 全量 async | LLM 调用是 IO 密集型，LangGraph 原生支持 async |

---

## 12. 成本估算

基于 Claude Sonnet，假设每次 Agent 调用平均 3000 input tokens + 1500 output tokens：

| 项目 | 数值 |
|------|------|
| 每轮 LLM 调用 | 4 次（4 个 Agent） |
| 平均辩论轮数 | 4 轮 |
| 报告生成 | 1 次 |
| 总 LLM 调用 | 17 次 |
| Input tokens（含增长） | ~55,000（因 transcript 压缩，增长可控） |
| Output tokens | ~25,500 |
| 预估单次辩论成本（全 Sonnet） | ~$0.30 - $0.50 |
| 混合调用优化后 | ~$0.15 - $0.25（Fact-Checker + Moderator 用 mini/Haiku） |

---

## 13. Prompt 工程注意事项

1. **结构化输出优先用 `with_structured_output`** 而不是在 prompt 里附 JSON schema。LangChain 会根据 provider 自动选最佳策略（Claude 用 tool_use、OpenAI 用 json_mode）

2. **论点 ID 引用机制**：在 Critic 的 prompt 中反复强调"你必须在 rebuttals 的 target_argument_id 字段引用 Advocate 的具体论点 ID"，并给出示例。这是辩论质量的关键

3. **防止角色坍塌**：Advocate prompt 中加入"只有当对方论证完全无法反驳时才将论点加入 concessions，不要轻易让步"。Critic 同理

4. **Fact-Checker 中立性**：明确"你不偏向任何一方。如果两方论证质量差异大，如实报告"

5. **Moderator 收敛判断**：在 prompt 中提供具体的评分锚点，比如"如果本轮只有 0-1 个新论点，且 concessions 数量增加，convergence_score 应在 0.7-0.9 之间"

6. **语言一致性**：system prompt 中加入"请使用与用户提问相同的语言输出所有内容"

---

## 14. 未来扩展

以下功能设计为可插拔模块，不耦合到核心辩论逻辑中，后续作为独立项目或插件接入：

### 14.1 Meta-Harness 集成

作为独立项目开发。辩论引擎预留的搜索空间包括：
- `prompts/` 下所有 prompt 构造函数
- `config.yaml` 中的参数（temperature、max_rounds、convergence_threshold）
- `core/transcript_manager.py` 的压缩策略
- `llm/router.py` 的模型分配
- LangGraph 图结构本身（节点顺序、条件函数的阈值）

接入方式：Meta-Harness 框架通过文件系统读取辩论引擎的代码和配置，修改后重新运行 eval，不需要辩论引擎做任何代码改动。

### 14.2 评估体系（Eval Harness）

- eval dataset：一批决策问题 + 黄金标准标注
- 多维度 LLM-as-judge：论点覆盖率、反驳质量、收敛行为、报告可操作性
- 回归测试管道：prompt 或参数变更后自动跑 eval 对比
- 接口：独立的 `eval/` 目录，通过 import 辩论引擎的 `main()` 批量运行

### 14.3 三层记忆架构

- **情景记忆（MemPalace 模式）**：每个 Agent 维护独立的记忆宫殿，辩论结束后写 diary entry，下次辩论按需检索。基于 ChromaDB，完全本地
- **语义记忆（LLM Wiki 模式）**：辩论结束后将报告编译进持久化 Markdown wiki，跨辩论积累领域知识
- 接入点：在每个 Agent node 的输入构造阶段，增加一个可选的"从记忆加载相关上下文"步骤。通过配置开关控制是否启用

### 14.4 Web UI

- 利用 LangGraph 的 `.astream_events()` 做实时辩论流推送
- 前端展示每个 Agent 的发言、论点状态流转、收敛曲线
- 最终报告可导出为 PDF/Markdown