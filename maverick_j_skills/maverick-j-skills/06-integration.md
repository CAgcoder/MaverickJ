# 多框架接入指南

> 本文件说明如何将辩论 Skill 接入不同的 Agent 框架。

---

## 1. Claude Code / Claude Cowork（单 LLM 自我角色切换）

**最简模式**: 不需要额外框架，Claude 自身依次扮演 4 个角色。

### 接入方式 A：作为 System Prompt

将 `SKILL.md` + `01-identity.md` + `02-protocol.md` 的内容注入 System Prompt。Claude 按照执行协议，在一次对话中完成多轮辩论。

### 接入方式 B：作为 Skill / Command

```
# .claude/commands/debate.md 或 .github/skills/debate/SKILL.md
触发词: "辩论分析"、"正反论证"、"should we..."

执行流程:
1. 读取 01-identity.md 和 02-protocol.md（理解角色和流程）
2. 读取 03-prompts.md（获取提示词模板）
3. 读取 04-schemas.md（明确输出格式）
4. 按 02-protocol.md 的执行顺序，依次扮演 Advocate → Critic → Fact-Checker → Moderator
5. 循环直到收敛
6. 生成 DecisionReport
```

### 单 LLM 执行注意事项

- 每个角色切换时，必须 **明确声明当前角色**，避免角色混淆
- 使用 `---` 分隔各角色输出，方便用户区分
- Moderator 的 `should_continue` 判定要诚实，不要为了展示更多轮次而强行继续

---

## 2. LangGraph（StateGraph 原生映射）

辩论协议与 LangGraph 的 StateGraph 天然对齐：

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(DebateState)

# 节点
workflow.add_node("round_setup", round_setup_node)
workflow.add_node("advocate", partial(advocate_node, router=router))
workflow.add_node("critic", partial(critic_node, router=router))
workflow.add_node("fact_checker", partial(fact_checker_node, router=router))
workflow.add_node("moderator", partial(moderator_node, router=router))
workflow.add_node("report", partial(report_node, router=router))

# 边
workflow.set_entry_point("round_setup")
workflow.add_edge("round_setup", "advocate")
workflow.add_edge("advocate", "critic")
workflow.add_edge("critic", "fact_checker")
workflow.add_edge("fact_checker", "moderator")

# 条件边: 继续 or 终止
workflow.add_conditional_edges(
    "moderator",
    should_continue,    # 返回 "continue" 或 "terminate"
    {"continue": "round_setup", "terminate": "report"}
)
workflow.add_edge("report", END)

app = workflow.compile()
```

**关键实现**:
- 每个 node 函数签名: `async def xxx_node(state: DebateState, router: ModelRouter) -> dict`
- node 返回 `dict` 表示状态增量更新（LangGraph 自动 merge）
- `router` 通过 `functools.partial()` 注入

---

## 3. OpenAI Agents SDK

```python
from agents import Agent, Runner

advocate = Agent(
    name="Advocate",
    instructions=ADVOCATE_SYSTEM_PROMPT,
    output_type=AgentResponse,
)

critic = Agent(
    name="Critic",
    instructions=CRITIC_SYSTEM_PROMPT,
    output_type=AgentResponse,
)

fact_checker = Agent(
    name="FactChecker",
    instructions=FACT_CHECKER_SYSTEM_PROMPT,
    output_type=FactCheckResponse,
)

moderator = Agent(
    name="Moderator",
    instructions=MODERATOR_SYSTEM_PROMPT,
    output_type=ModeratorResponse,
)

# Orchestrator 控制轮转
orchestrator = Agent(
    name="DebateOrchestrator",
    instructions="按 Advocate → Critic → FactChecker → Moderator 顺序编排辩论轮次",
    handoffs=[advocate, critic, fact_checker, moderator],
)

result = await Runner.run(orchestrator, input=question)
```

---

## 4. CrewAI

```python
from crewai import Agent, Task, Crew, Process

advocate = Agent(
    role="Advocate",
    goal="Build strongest pro-side case for the decision",
    backstory=ADVOCATE_SYSTEM_PROMPT,
    llm=your_llm,
)

critic = Agent(
    role="Critic",
    goal="Systematically challenge pro-side and build con-side case",
    backstory=CRITIC_SYSTEM_PROMPT,
    llm=your_llm,
)

fact_checker = Agent(
    role="FactChecker",
    goal="Evaluate logical consistency and factual accuracy",
    backstory=FACT_CHECKER_SYSTEM_PROMPT,
    llm=your_llm,
)

moderator = Agent(
    role="Moderator",
    goal="Judge convergence and guide debate focus",
    backstory=MODERATOR_SYSTEM_PROMPT,
    llm=your_llm,
)

# 定义每轮 Tasks
def create_round_tasks(round_num):
    return [
        Task(description=f"Round {round_num}: Present pro-side arguments", agent=advocate),
        Task(description=f"Round {round_num}: Challenge and rebut", agent=critic),
        Task(description=f"Round {round_num}: Fact-check all arguments", agent=fact_checker),
        Task(description=f"Round {round_num}: Judge convergence", agent=moderator),
    ]

crew = Crew(
    agents=[advocate, critic, fact_checker, moderator],
    tasks=create_round_tasks(1),  # 动态追加后续轮次
    process=Process.sequential,
)
```

---

## 5. AutoGen

```python
from autogen import AssistantAgent, GroupChat, GroupChatManager

advocate = AssistantAgent("Advocate", system_message=ADVOCATE_SYSTEM_PROMPT)
critic = AssistantAgent("Critic", system_message=CRITIC_SYSTEM_PROMPT)
fact_checker = AssistantAgent("FactChecker", system_message=FACT_CHECKER_SYSTEM_PROMPT)
moderator = AssistantAgent("Moderator", system_message=MODERATOR_SYSTEM_PROMPT)

groupchat = GroupChat(
    agents=[advocate, critic, fact_checker, moderator],
    messages=[],
    max_round=20,  # 4 agents × 5 rounds
    speaker_selection_method="round_robin",  # 固定轮转顺序
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
manager.initiate_chat(message=f"Decision question: {question}")
```

---

## 6. 通用适配清单

无论使用何种框架，确保以下要素到位:

| 要素 | 说明 |
|------|------|
| ✅ 4 个 Agent 角色 | Advocate, Critic, Fact-Checker, Moderator |
| ✅ 固定执行顺序 | A → C → FC → M (每轮) |
| ✅ 结构化输出 | 每个 Agent 输出符合 04-schemas.md 的 JSON |
| ✅ 论点 ID 系统 | ADV-R{n}-{nn} / CRT-R{n}-{nn} 格式 |
| ✅ 论点注册表 | 跟踪每个论点的生命周期 (见 05-registry.md) |
| ✅ 收敛终止逻辑 | Moderator 判定 + 连续高分 + 最大轮数兜底 |
| ✅ 报告生成 | 终止后生成结构化 DecisionReport |
