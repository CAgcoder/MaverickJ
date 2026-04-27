# MaverickJ 供应链决策特化扩展（MVP）

## Context

MaverickJ 当前是一个通用决策辩论引擎（advocate / critic / fact_checker / moderator / report_generator + LangGraph 编排）。用户希望基于现有架构无缝叠加一个**供应链辅助决策模式（supply_chain mode）**，把通用辩论升级为：
- 「激进降本派 vs 极端风控派」的双视角对抗
- 强制依赖工具计算（EOQ / Monte Carlo / TCO）+ 真实/模拟数据（SQLite ERP + yfinance + 事件库）
- 供应链特化的诡辩检测（局部最优陷阱、牛鞭效应盲区、沉没成本谬误等）
- ToT 融合阶段：抽取高分论据 → 融合草案 → 双方建设性批评 → 定型决策
- 决策矩阵 + 数据证据 + 少数派报告 + 黑天鹅熔断预案

**目标**：用现有架构作为标准底座，**最小侵入 + 最大复用**地新增一个 `maverickj/supply_chain/` 子包，把所有特化逻辑内聚于此；通过 `config.debate.mode = "supply_chain"` 切换。`general` 模式行为零回归。

**用户已决策（2026-04-27）**：
1. yfinance → 核心 dependencies（不放 optional extras）
2. 工具引用 → **硬约束 + Round 1 例外**（Round 1 advocate 允许 1-2 个无引用的"战略方向论点"；Round 2+ 全部强制）
3. ToT critique → **固定 1 轮**（MVP 简单稳定）
4. fusion_synthesis 阈值 → **综合 ≥ 8 + 事实性硬门槛 ≥ 7**

---

## 总体架构（5 层映射到 LangGraph 拓扑）

```
START
 → round_setup           [复用]
 → data_warmup           [新增] 拉 ERP + yfinance + events，跑基线 EOQ/MC/TCO，写入 state.tool_calls + current_round_data_pack
 → advocate              [复用节点 + 新 cost_advocate prompt]   激进降本派
 → critic                [复用节点 + 新 risk_critic prompt]     极端风控派
 → fact_checker          [复用节点 + 扩展 prompt]               诡辩检测器（含 6 种供应链谬误 + 工具引用校验 + 事实性/逻辑评分）
 → moderator             [复用节点 + 扩展 prompt]               裁判（+ 可行性/切题度评分）
 → should_continue       [完全复用，零修改]
       ├─ continue → round_setup
       └─ terminate → fusion_synthesis        [新增] 抽取 ≥ 8 分论据，生成融合草案
                     → convergence_critique   [新增] 双方对草案做 1 轮建设性批评
                     → fusion_finalize        [新增] 合并批评，生成 final_fused_decision
                     → report                 [复用节点 + 扩展 prompt]   产出决策矩阵+数据证据+少数派+熔断预案
                     → END
```

**关键设计决策**：
- **工具调用模式 = Hybrid 双层**：
  - **Tier 1 — 基线预执行**：`data_warmup` 节点跑全量基线（EOQ / MC / TCO / ERP / market / events），保证可信数据底座，结果通过 `state.current_round_data_pack` 注入 user message
  - **Tier 2 — Agent 按需调用**：cost_advocate / risk_critic / fact_checker 通过 LangChain `bind_tools()` 暴露工具列表给 LLM，Agent 可在论证时追加调用（如 sweep 不同 demand 值的 EOQ 敏感性、跑特定参数的 MC 验证黑天鹅）
  - **统一记录**：所有调用都流经 `ToolCallRegistry`，写入 `state.tool_calls`，引用契约统一
- **Red/Blue 切换 = Prompt 级 dispatch**，不分裂节点。`prompts/advocate.py` 和 `prompts/critic.py` 内根据 `state.config.mode` 路由到 `supply_chain.prompts.cost_advocate` / `risk_critic`。这样 `graph/nodes/` 完全复用。
- **新拓扑放在新文件**：`maverickj/supply_chain/builder.py:build_supply_chain_graph()`，不动 `maverickj/graph/builder.py`。

---

## 模块布局

### 新增文件

```
maverickj/supply_chain/
├── __init__.py
├── tools/
│   ├── eoq.py                  # calc_eoq(demand, setup_cost, holding_cost) → EOQ + 持仓节省
│   ├── monte_carlo.py          # run_monte_carlo(mean, std_dev, simulations=1000) → 断货/积压概率 + P50/P95
│   ├── tco.py                  # calc_tco(unit_price, freight, tariff, capital_cost, defect_rate, ...) → TCO 拆解
│   ├── market_data.py          # fetch_and_cache(tickers) / fetch_cached() — yfinance 包装 + JSON 缓存
│   ├── events.py               # query_active_events(region?, type?) — 读 events.json mock
│   ├── erp.py                  # get_inventory/get_suppliers/get_forecast/get_full_snapshot — SQLite 查询
│   ├── registry.py             # ToolCallRegistry：每次调用都生成 ToolCallRecord 写入 state.tool_calls
│   └── langchain_tools.py      # 把上述函数包装成 LangChain @tool 列表，供 Tier 2 bind_tools 使用
├── data/
│   ├── seed.sql                # CREATE TABLE Inventory / Supplier / Sales_Forecast + 种子数据
│   ├── data_loader.py          # init_db(db_path) 幂等建表
│   ├── events.json             # mock OpenCLI 事件（罢工/油价/地缘等）
│   └── market_cache.json       # yfinance 预拉缓存（含 fetched_at 时间戳）
├── schemas/
│   ├── tool_call.py            # ToolCallRecord(id, tool_name, inputs, outputs, summary, invoked_at_round, invoked_by)
│   ├── decision.py             # DecisionOption / CircuitBreaker / MultiDimScore
│   ├── fusion.py               # FusionDraft / ConvergenceCritique / FusedDecision
│   └── fallacy.py              # SupplyChainFallacyType Enum（白名单提示用，非强制）
├── prompts/
│   ├── cost_advocate.py        # build_cost_advocate_system_prompt + user_message（注入 data_pack）
│   ├── risk_critic.py          # 同上
│   ├── fact_checker.py         # 扩展通用版：增加 6 种供应链谬误库 + 工具引用校验规则 + 事实性/逻辑评分
│   ├── moderator.py            # 扩展通用版：增加可行性/切题度评分（per-argument）
│   ├── fusion_synthesizer.py   # 抽取 ≥ 8 分论据 + 生成融合草案
│   ├── convergence_critic.py   # 「不创造新论点，只对草案做 1-3 条建设性批评 + 是否 endorsement」
│   └── report_generator.py     # 扩展通用版：要求填充 decision_matrix / data_evidence / minority_report / circuit_breakers
├── agents/
│   └── supply_chain_agent.py   # SupplyChainAgent(BaseAgent) — 扩展 invoke() 支持 tools 参数（bind_tools + 工具调用循环）
├── nodes/
│   ├── data_warmup.py          # async def data_warmup_node(state, router) — Tier 1 基线工具预执行
│   ├── fusion_synthesis.py     # async def fusion_synthesis_node — 阈值过滤 + LLM 生成草案
│   ├── convergence_critique.py # async def convergence_critique_node — 节点内串行调 cost_advocate + risk_critic
│   └── fusion_finalize.py      # async def fusion_finalize_node — 合并 critiques 写 final_fused_decision
├── output_extras.py            # render_supply_chain_extras(report, state) — 渲染 4 个新字段为 Markdown
└── builder.py                  # build_supply_chain_graph(router) — 新拓扑
```

### 修改既有文件（最小集合）

| 文件 | 改动 |
|---|---|
| `maverickj/schemas/debate.py` | `DebateConfig` 加 `mode: Literal["general", "supply_chain"] = "general"`；`DebateState` 加 5 个供应链字段（`tool_calls`、`current_round_data_pack`、`fusion_draft`、`convergence_critiques`、`final_fused_decision`），全部 Optional/默认空 |
| `maverickj/schemas/arguments.py` | `Argument` 加 `tool_call_ids: list[str] = []` |
| `maverickj/schemas/report.py` | `DecisionReport` 加 4 个 Optional 字段：`decision_matrix`、`data_evidence`、`minority_report`、`circuit_breakers` |
| `maverickj/schemas/agents.py` | `FactCheck` 加 `factuality_score`/`logic_score` Optional float；`ModeratorResponse` 加 `feasibility_scores`/`relevance_scores: dict[str, float]` |
| `maverickj/schemas/config.py` | `DebateEngineConfig` 加 `supply_chain: SupplyChainConfig` 块；`AgentModelConfig` 加 `fusion_synthesizer`/`convergence_critic` 角色 |
| `maverickj/llm/router.py` | `AGENT_ROLES` 加 `"fusion_synthesizer"`、`"convergence_critic"`，未配置时回退 `report_generator` 模型 |
| `maverickj/prompts/advocate.py` | 入口处 dispatch：`if state.config.mode == "supply_chain": return cost_advocate.build_*(...)` |
| `maverickj/prompts/critic.py` | 同上，dispatch 到 `risk_critic` |
| `maverickj/prompts/fact_checker.py` | 同上 dispatch |
| `maverickj/prompts/moderator.py` | 同上 dispatch |
| `maverickj/prompts/report_generator.py` | 同上 dispatch |
| `maverickj/main.py` | `run_debate()` 根据 `config.debate.mode` 选 `build_debate_graph` 或 `build_supply_chain_graph` |
| `maverickj/output/renderer.py` | 末尾追加 5 行：`if report.decision_matrix or report.circuit_breakers: lines.extend(render_supply_chain_extras(report, state))` |
| `config.yaml` | 新增 `supply_chain` 配置块 + 2 个新 agent 角色配置 |
| `pyproject.toml` | dependencies 加 `yfinance>=0.2`、`numpy>=1.26`（蒙特卡洛用） |
| `.gitignore` | 加 `maverickj/supply_chain/data/seed.db` |

### 新增 demo

`examples/supply_chain_demo.py`：跑「SKU-A21 是否切换到东南亚供应商」完整辩论。

---

## 关键接口与数据流

### B. 工具调用机制（Hybrid 双层）

#### Tier 1 — `data_warmup_node` 基线预执行
- Round 1：拉所有静态数据（ERP 全表 / yfinance 缓存 / events），跑基线 EOQ + MC + TCO，记录 `TC-001 ~ TC-00X`（前缀标记 `source="warmup"`）
- Round 2+：根据上一轮 `moderator.guidance_for_next_round` 决定是否追加基线计算
- 每次调用 → `ToolCallRecord` 写入 `state.tool_calls[id]`，摘要塞进 `state.current_round_data_pack`，作为 user message 的"事实弹药包"

#### Tier 2 — Agent 按需调用（cost_advocate / risk_critic / fact_checker）
- 通过 `SupplyChainAgent.invoke(system_prompt, user_message, output_schema, tools=...)` 在 LLM 层启用 LangChain `bind_tools()`
- 暴露的工具列表（`tools/langchain_tools.py` 中以 `@tool` 装饰器定义）：
  - `calc_eoq_tool(demand, setup_cost, holding_cost)` 
  - `run_monte_carlo_tool(mean, std_dev, simulations)`
  - `calc_tco_tool(...)`
  - `query_supplier_tool(region?, max_price?, min_otif?)` — 查询供应商表
  - `query_events_tool(region?, type?, severity?)` — 查询事件库
  - `query_market_tool(ticker)` — 查询缓存的市场数据
- LLM 在生成结构化输出（`AgentResponse`）前可以多轮 tool call：例如 advocate 调用 `calc_eoq_tool` 三次 sweep 不同 demand 值，再综合写论点
- 每次 Tier 2 调用同样写入 `state.tool_calls`，前缀标记 `source="agent:cost_advocate"` 等
- LangChain provider 适配：`bind_tools()` 已在 Claude / OpenAI / Gemini 上原生支持，`SupplyChainAgent` 内部用 `model.bind_tools(tools).with_structured_output(schema)` 组合
- **回退路径**：若某 provider 不支持组合（如某些 Gemini 版本），降级到 Tier 1 only 模式（在 router 层判断）

#### Agent 引用契约（不变）
- 每个 `Argument.evidence` 必须形如 `"TC-003: 蒙特卡洛 1000 次模拟显示，若切换到 SUP-SEA-03，断货概率从 4% 升至 18%（P95 缺货 320 件）"`
- `Argument.tool_call_ids` 必须列出所有引用的 ID（无论来源是 Tier 1 还是 Tier 2）
- **Round 1 例外**：advocate 允许 1-2 个无 `tool_call_ids` 的「战略方向论点」，需在 `claim` 字段以 `[战略方向]` 前缀标注；Round 2+ 完全禁止
- fact_checker 强校验：
  - 引用的 ID 必须在 `state.tool_calls` 中存在 → 否则 `fallacy_type="fabricated_evidence"` + `verdict=flawed`
  - Round 2+ 任何 `tool_call_ids=[]` 且非战略方向论点 → `verdict=flawed` + `factuality_score=0`
  - 数值是否与 `ToolCallRecord.outputs` 一致 → 选择性引用扣事实性分

### C. 数据源（MVP 极简）

**SQLite seed.sql 三表**：
- `Inventory(sku, name, on_hand_units, safety_stock_units, holding_cost_per_unit_year, setup_cost_per_order, unit_cost)`
- `Supplier(supplier_id, name, region, otif_rate, defect_rate, lead_time_days, unit_price, moq)`
- `Sales_Forecast(sku, week_ahead, mean_demand, std_dev)` — 复合主键

**种子数据**：3 SKU × 5 供应商（local/sea/eu/us 覆盖）× 3 周预测，足够支撑「是否切换供应商」的有意义辩论。

**yfinance**：核心依赖（用户决策）。`fetch_and_cache(tickers, cache_path)` 启动时调用一次写 JSON；`fetch_cached()` 后续读缓存。`config.supply_chain.market_data.cache_ttl_hours: 6`，过期才刷新。`offline_mode: true` 时强制用缓存（CI/演示用）。
默认 tickers：
- `CL=F` — WTI 原油期货（影响海运/陆运成本）
- `NG=F` — Henry Hub 天然气期货（影响生产能耗 + 化工原料）
- `EUR=X` — 欧元/美元汇率（影响欧洲采购）

**events.json mock**：5-10 条预设事件（罢工/油价突破/地缘等），每条含 `{id, type, region, headline, severity, active, since}`。V1.1 替换为真实 OpenCLI，接口契约 MVP 已锁定。

### D. Red/Blue Prompt 设计（核心 IP 区）

**`cost_advocate.py` system prompt 关键内容**：
- 角色：CFO/采购总监视角，**唯一目标是降低 TCO**
- 行为规则：必须从 `data_pack.baseline_tco` 出发，找出可压缩成本项；可调用 `yfinance.market` 论证汇率/油价红利；引用 `data_pack.suppliers` 找最低单价
- 反方反驳处理：若 risk_critic 用 monte_carlo 数据反驳，必须用 calc_tco 折算"风险等价成本"反击（不能光说"风险可控"）
- ID 规范：`COST-R{N}-NN`（仍可与现有 `ADV-` 前缀并存，但供应链模式下用专属前缀更清晰）

**`risk_critic.py` system prompt 关键内容**：
- 角色：COO/供应链总监视角，**唯一目标是供应链韧性**
- 行为规则需覆盖**三大风险支柱**（缺一不可）：
  1. **运营风险**：从 `data_pack.baseline_mc` 出发，用蒙特卡洛量化断货/积压概率；引用 `data_pack.suppliers.otif_rate` + `lead_time_days` 质疑供应可靠性
  2. **市场风险**：从 `data_pack.market`（油价/天然气/汇率）出发，量化跨国采购的成本波动暴露；调用 `query_market_tool` 检验趋势
  3. **地缘政治风险**：从 `data_pack.events` 出发，识别罢工 / 港口封锁 / 制裁 / 关税战等事件，并按 region 关联到候选供应商；调用 `query_events_tool(region=候选区域, severity="high")` 主动扫描；对每个高地缘风险事件，必须给出"概率 × 影响"的定性评估（事件发生时对供应链的具体冲击：断供天数、替代成本等）
- 反方反驳处理：若 cost_advocate 用 calc_tco 算出短期降本，必须用 monte_carlo 算出"概率加权损失"反击；若涉及跨境/海运路线，必须叠加 market + 地缘事件的尾部风险
- ID 规范：`RISK-R{N}-NN`
- **谬误规避自我提醒**：不得犯 single_point_failure（必须考虑 backup 供应商）、不得犯 lead_time_optimism（必须用 OTIF 加权）

### E. 诡辩检测器（fact_checker 扩展）

**6 种供应链谬误**（在 `supply_chain/schemas/fallacy.py` 定义为 Enum，但 `FactCheck.fallacy_type` 字段保持 str 类型，Enum 仅作为白名单提示）：
- `local_optima_trap` — 局部最优陷阱（省运费 10% 但仓储 +20%）
- `bullwhip_blindspot` — 牛鞭效应盲区
- `sunk_cost_fallacy` — 沉没成本（死守劣质供应商）
- `single_point_failure` — 单点故障（只看一家供应商）
- `safety_stock_denial` — 否认安全库存必要性
- `lead_time_optimism` — 总用最乐观 lead time
+ 通用谬误：`straw_man`/`slippery_slope`/`confirmation_bias` 等

**fact_checker prompt 三块新内容**：
1. 谬误库（每种给定义 + 识别线索 + 2-3 个典型话术示例）
2. 工具引用校验规则（如上 B 节）
3. 评分要求：每个 FactCheck 输出 `factuality_score`（0-10，与工具引用准确度强挂钩）+ `logic_score`（0-10，谬误类型直接扣分）

### E.3 评分维度归属

| 维度 | 评分者 | Schema 字段 |
|---|---|---|
| 论据事实性 | fact_checker | `FactCheck.factuality_score` |
| 逻辑严密性 | fact_checker | `FactCheck.logic_score` |
| 方案可行性 | moderator | `ModeratorResponse.feasibility_scores: dict[arg_id, float]` |
| 切题度 | moderator | `ModeratorResponse.relevance_scores: dict[arg_id, float]` |

### F. ToT 融合三阶段

**`fusion_synthesis_node`**：
- 遍历 `state.argument_registry` 中所有 `ACTIVE` 或 `MODIFIED` 的论点
- 计算综合分 = (factuality + logic + feasibility + relevance) / 4
- **入选规则**：综合分 ≥ 8.0 **AND** factuality_score ≥ 7.0（用户决策）
- 把入选论点 ID + 分数喂给 `fusion_synthesizer` LLM，输出 `FusionDraft(high_score_arguments, proposed_consensus, consensus_actions, open_questions)`
- 写入 `state.fusion_draft`

**`convergence_critique_node`**（节点内串行）：
- 调 `cost_advocate` 用 `convergence_critic` prompt 对 `fusion_draft` 做 1-3 条 critique，必须 `final_endorsement: bool`
- 调 `risk_critic` 同上
- 两人都不能创造新论点，只能 amend 草案
- 结果合并写入 `state.convergence_critiques: list[ConvergenceCritique]`

**`fusion_finalize_node`**：
- LLM 合并双方 critiques，输出 `FusedDecision(final_consensus, accepted_amendments, rejected_amendments_with_reason, remaining_disagreements)`
- 写入 `state.final_fused_decision`
- `remaining_disagreements` 后续直接进入 `DecisionReport.minority_report`

### G. 报告升级

**`DecisionReport` 新增 4 个 Optional 字段**：
```
decision_matrix: list[DecisionOption]     # 决策矩阵每行：path_name / expected_tco_usd / implementation_cost_usd / risk_warnings / supporting_tool_calls
data_evidence: list[ToolCallRecord]       # 报告引用的关键 ToolCallRecord 子集
minority_report: list[str]                # 来自 final_fused_decision.remaining_disagreements
circuit_breakers: list[CircuitBreaker]    # 黑天鹅预案：trigger_condition / trigger_metric / threshold_value / fallback_action / rationale
```

**report_generator prompt 新增要求**：
- 必须从 `state.final_fused_decision.consensus_actions` 派生 2-3 个 `DecisionOption`（推荐方案 + 1-2 个备选）
- 必须从 `state.tool_calls` 抽取 EOQ/MC/TCO 关键结果填 `data_evidence`
- 必须根据 `state.tool_calls` 中的 `events` 和 `market` 数据推导至少 1-2 个 `CircuitBreaker`（如"WTI 油价突破 $95/桶 → 切回本地供应商 SUP-LOCAL-01"）

**`output/renderer.py` 改动最小**：仅追加 5 行 dispatch；所有新字段渲染逻辑放在 `supply_chain/output_extras.py`（决策矩阵表 + 数据证据展开 + 少数派报告区块 + 熔断预案表）。`general` 模式 renderer 行为零变化。

### H. 配置与运行入口

**`config.yaml` 新增**：
```yaml
agents:
  fusion_synthesizer: { provider: claude, model: claude-sonnet-4-6, temperature: 0.4, max_tokens: 8192 }
  convergence_critic: { provider: claude, model: claude-sonnet-4-6, temperature: 0.5, max_tokens: 6144 }

debate:
  mode: general   # 或 supply_chain

supply_chain:
  data_path: ./maverickj/supply_chain/data
  market_data:
    tickers: [CL=F, NG=F, EUR=X]   # WTI 原油 / Henry Hub 天然气 / 欧元美元
    cache_ttl_hours: 6
    offline_mode: false
  monte_carlo:
    simulations: 1000
    confidence_levels: [0.5, 0.95]
  fusion:
    composite_score_threshold: 8.0
    factuality_score_threshold: 7.0
    critique_max_rounds: 1
  agent_tools:                     # Tier 2 按需调用配置
    enabled: true                  # false 时降级为 Tier 1 only
    max_tool_calls_per_turn: 5     # 单次 invoke 内最多工具调用数（防 LLM 死循环）
```

**CLI**：复用现有 `debate` 命令 + 新增 `--mode supply_chain` 参数（覆盖配置）。不引入新命令。

---

## 执行步骤建议（4 周 / 1 人）

| 阶段 | 任务 | 依赖 | 估时 |
|---|---|---|---|
| 1 | Schemas 扩展（`debate.py` / `arguments.py` / `report.py` / `agents.py` / `config.py`）+ supply_chain 子包骨架 | — | 2d |
| 2 | 工具层（eoq / monte_carlo / tco / erp / events / market_data + registry + seed.sql 种子数据） | 1 | 3d |
| 2b | LangChain `@tool` 包装层（langchain_tools.py） + provider 兼容性测试 | 2 | 1d |
| 3 | SupplyChainAgent 子类（扩展 invoke 支持 tools）+ data_warmup 节点 | 1, 2, 2b | 2d |
| 4 | cost_advocate + risk_critic prompts（含三大风险支柱）+ 5 个通用 prompt 的 dispatch 改造 | 1 | 2d |
| 5 | fact_checker + moderator prompts 扩展（谬误库 + 评分维度） | 4 | 2d |
| 6 | fusion_synthesis + convergence_critique + fusion_finalize 三节点 + fusion 子 schemas | 1, 5 | 4d |
| 7 | report_generator prompt 扩展 + output_extras 渲染 | 1, 6 | 2d |
| 8 | builder.py 新拓扑 + main.py mode dispatch + config.yaml + pyproject.toml | 1-7 | 1d |
| 9 | examples/supply_chain_demo.py + 端到端联调 + prompt 微调 | 1-8 | 3d |
| **合计** | — | — | **~22d (4.5 周)** |

并行优化：阶段 2 与阶段 4 可并行；阶段 2b 仅多 1 天用于 LangChain tool 包装与跨 provider 适配。

---

## 关键文件路径（实施时重点关注）

**修改优先级最高的 5 个**：
- [maverickj/schemas/debate.py](maverickj/schemas/debate.py) — DebateConfig + DebateState 扩展（最先改，所有下游依赖它）
- [maverickj/schemas/report.py](maverickj/schemas/report.py) — DecisionReport 扩展
- [maverickj/main.py](maverickj/main.py) — run_debate 的 mode dispatch
- [maverickj/output/renderer.py](maverickj/output/renderer.py) — 末尾 5 行 dispatch
- [config.yaml](config.yaml) — supply_chain 配置块 + 2 个新 agent 角色

**新增最关键的 5 个**：
- `maverickj/supply_chain/builder.py` — 新拓扑（参考 [graph/builder.py](maverickj/graph/builder.py) 镜像写）
- `maverickj/supply_chain/nodes/data_warmup.py` — 工具预执行的核心节点
- `maverickj/supply_chain/tools/registry.py` — ToolCallRegistry，所有工具调用流经此处
- `maverickj/supply_chain/prompts/cost_advocate.py` — 激进降本派 IP 核心
- `maverickj/supply_chain/prompts/risk_critic.py` — 极端风控派 IP 核心

**绝对不动的 3 个（可复用基础设施）**：
- [maverickj/agents/base.py](maverickj/agents/base.py) — BaseAgent.invoke + JSON 修复链路（已稳定）
- [maverickj/graph/conditions.py](maverickj/graph/conditions.py) — should_continue（路由目标由 builder 决定，函数本身无需改）
- [maverickj/core/argument_registry.py](maverickj/core/argument_registry.py) — 论点生命周期跟踪（直接复用）

---

## 复用清单（无需重写）

| 已有组件 | 用途 | 复用方式 |
|---|---|---|
| `BaseAgent.invoke()` | LLM 调用 + JSON 多层修复 + 重试 | 所有新 Agent 继承或直接用 |
| `ArgumentRegistry` | 论点生命周期 (active/rebutted/conceded/modified) | cost_advocate/risk_critic 注册时复用，加 `tool_call_ids` 字段 |
| LangGraph + DebateState | DAG 编排 + 状态传递 | 新 builder 镜像通用 builder 模式 |
| `should_continue` | 收敛判定（max_rounds + convergence_score） | 完全复用，仅改 builder 的路由目标 |
| `ModelRouter` | 按 role 分配模型 + fallback | 新增 2 个 role 即可 |
| `prompts/{role}.py` 函数模式 | system_prompt + user_message 构造 | 新 prompt 镜像同一签名 |
| Event Stream (`events.py`) | 进度回调 | 可选新增 SupplyChainEvent 类型 |
| 成本追踪 (`llm/cost.py`) | token 计量 | 直接复用 |

---

## V1.1 延后（MVP 不实现）

- OpenCLI 真实爬虫（`events.py` 接口契约 MVP 已锁定，替换实现即可）
- yfinance 实时调用（同上，MVP 用缓存模式）
- 多 Agent 派系扩展（环保派、合规派 ESG 等）
- ToT 多轮 critique 循环（MVP 锁定 1 轮）
- 决策矩阵敏感性分析（sweep demand/price 区间生成多场景）
- pytest 单测全覆盖（MVP 仅新增 smoke test，端到端验证为主）
- 多维度评分的可视化（雷达图等，MVP 仅 Markdown 表格）
- 工具调用图谱 mermaid 可视化

---

## 验证方案（端到端）

实施完成后通过以下步骤验证：

### 1. 单元级
```bash
# 工具函数纯计算
python -c "from maverickj.supply_chain.tools.eoq import calc_eoq; print(calc_eoq(demand=1200, setup_cost=50, holding_cost=2.4))"
python -c "from maverickj.supply_chain.tools.monte_carlo import run_monte_carlo; print(run_monte_carlo(mean=1200, std_dev=280, simulations=1000))"

# SQLite 数据加载
python -c "from maverickj.supply_chain.data.data_loader import init_db, get_full_snapshot; init_db('maverickj/supply_chain/data/seed.db'); print(get_full_snapshot())"

# yfinance 缓存
python -c "from maverickj.supply_chain.tools.market_data import fetch_and_cache; print(fetch_and_cache(['CL=F', 'CNY=X'], 'maverickj/supply_chain/data/market_cache.json'))"
```

### 2. General 模式回归（确保零回归）
```bash
debate "Should we adopt microservices?" --max-rounds 2
# 预期：行为完全与改动前一致，新字段全部 None/[]
```

### 3. Supply Chain 模式端到端
```bash
python examples/supply_chain_demo.py
# 或
debate "我们应该把 SKU-A21 主供应商从本地切换到东南亚 SUP-SEA-03 吗？" --mode supply_chain
```

**验证 checklist**：
- [ ] Tier 1：`data_warmup` 节点跑完，`state.tool_calls` 至少包含 5 条 `source="warmup"` 记录
- [ ] Tier 2：至少 1 条 `state.tool_calls` 记录的 `source` 形如 `"agent:cost_advocate"` 或 `"agent:risk_critic"`（证明 LLM 自主调用了工具）
- [ ] cost_advocate 的所有 Round 2+ 论点 `tool_call_ids` 非空
- [ ] risk_critic 论证覆盖三大支柱：至少 1 个论点引用 `data_pack.events`（地缘）+ 1 个引用 `data_pack.market`（油气/汇率）+ 1 个引用 `baseline_mc`（运营）
- [ ] fact_checker 至少触发 1 次供应链谬误检测（`fallacy_type` 是 6 种之一）
- [ ] moderator 输出的 `feasibility_scores` 和 `relevance_scores` 覆盖所有 active 论点
- [ ] `state.fusion_draft.high_score_arguments` 非空（综合 ≥ 8 + 事实 ≥ 7 的论点）
- [ ] `state.convergence_critiques` 包含 cost_advocate 和 risk_critic 各 1 条
- [ ] 最终 `final_report.decision_matrix` 至少 2 个 `DecisionOption`
- [ ] 最终 `final_report.circuit_breakers` 至少 1 条（含 yfinance ticker 触发条件，如 `CL=F` 或 `NG=F` 或 `EUR=X`）
- [ ] 生成的 Markdown 报告（`reports/*.md`）包含「决策矩阵」「数据证据」「少数派报告」「黑天鹅预案」四个 H2 区块
- [ ] 总成本（`metadata.total_cost_usd`）控制在合理范围内（5 轮辩论 + ToT，启用 Tier 2 后 < $1.0）

### 4. 配置切换验证
```bash
# 同一个问题用 general vs supply_chain 跑，对比报告差异
debate "Same question" --mode general > /tmp/general.md
debate "Same question" --mode supply_chain > /tmp/sc.md
diff /tmp/general.md /tmp/sc.md
# 预期：sc 报告多出 4 个 H2 区块；general 报告与改动前一致
```