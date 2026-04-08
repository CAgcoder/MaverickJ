# 多 Agent 辩论式决策引擎（Python 版）

用户输入商业决策问题，系统启动 4 个专职 Agent 进行多轮结构化辩论，最终输出包含正反论点、关键分歧和建议的决策报告。

## 核心架构

- **Advocate**（正方论证者）：构建最强正方论证
- **Critic**（反方批评者）：系统性挑战正方论点
- **Fact-Checker**（事实校验者）：中立审视双方论证质量
- **Moderator**（主持人）：控制辩论节奏，判断收敛

## 技术栈

- Python 3.12+
- LangGraph（多 Agent 状态图编排）
- LangChain Core（统一模型抽象层）
- Pydantic v2（数据校验）
- 支持 Claude / OpenAI / Gemini 多 Provider

## 快速开始

### 选项 A：🐳 Docker 交互式模式（推荐）

**最简便的方式，一键启动交互式终端辩论：**

```bash
cd debate-engine-py

# 1. 复制并配置 API Key
cp .env.example .env
# 编辑 .env，填入至少一个 Provider 的 API Key

# 2. 构建镜像
docker compose build

# 3. 启动交互式终端
docker compose run --rm debate
```

**使用流程：**
```
欢迎信息
↓
输入决策问题（如"我们应该将 Java 迁移到 Go 吗？"）
↓
输入背景信息（可选，按 Enter 跳过）
↓
实时观看 4 个 Agent 的完整发言（彩色显示，包含推理过程与证据）
↓
辩论结束后显示简要结论
↓
选择：[1] 新话题 / [2] 保存完整报告 / [3] 退出
```

### 选项 B：⚡ 本地 Python 交互式模式

```bash
cd debate-engine-py

# 1. 安装依赖
pip install -e .

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env

# 3. 启动交互式模式
debate-interactive
```

### 选项 C：🔧 CLI 一次性模式（原有方式）

适合自动化脚本或一次性执行：

```bash
cd debate-engine-py

# 安装依赖
pip install -e .

# 方式 1: 直接命令行
python -m src.main "我们应该将 Java 后端迁移到 Go 吗？" "50人团队，Spring Boot 3年"
# 输出：debate-report.md

# 方式 2: 示例脚本
python examples/java_to_go.py
python examples/build_vs_buy.py
```

## 终端输出特性

交互式模式使用 **Rich** 库提供增强的终端体验：

### 彩色角色分组

每个 Agent 的发言用彩色 Panel 包裹，便于区分：

- **🟢 正方论证者** (绿色) — 显示正方论点、反驳、让步、信心变化
- **🔴 反方批评者** (红色) — 显示反方论点、反驳、让步、信心变化
- **🔍 事实校验者** (蓝色) — 显示事实检查结果、逻辑谬误、整体评估
- **⚖️  主持人** (黄色) — 显示轮次总结、关键分歧、**收敛分数进度条**、下轮焦点

### 详细内容展示

每个论点显示完整信息：
```
✅ [ADV-R1-01] 论点标题
   推理: 详细推理过程...
   证据: 支撑证据或数据...
```

### 收敛可视化

Moderator 的收敛分数动态显示：
```
██████████░░░░░░░░░░ 70%
```

---

## 配置

### 环境变量

创建 `.env` 文件配置 API Key（至少需要一个）：

```bash
# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# OpenAI (GPT)
OPENAI_API_KEY=sk-xxxxx

# Google (Gemini)
GOOGLE_API_KEY=xxxxx
```

参考 `.env.example` 获取完整模板。

### 辩论参数

编辑 `config.yaml` 选择模型和辩论参数：

```yaml
# 统一切换模型
default_provider: claude
default_model: claude-sonnet-4-20250514
default_temperature: 0.7

# 辩论参数
debate:
  max_rounds: 5              # 最大轮数
  convergence_threshold: 2   # 连续收敛轮数阈值
  convergence_score_target: 0.8  # 收敛分数目标
  language: auto             # 自动检测语言
```

支持为不同 Agent 配置不同模型（混合调用模式），详见 `config.yaml` 中的注释。

### Docker 配置

**使用 Docker 时：**

1. 创建 `.env` 文件并填入 API Key（Dockerfile 不会复制 `.env`，运行时动态加载）
2. `docker compose` 通过 `env_file: .env` 自动加载
3. Volume mount `config.yaml` 允许运行时修改配置（详见 `docker-compose.yml`）

**本地 Python 时：**

Dockerfile 和 docker-compose.yml 无需使用，直接使用本地 `.env` 文件。

---

## 项目结构

```
debate-engine-py/
├── Dockerfile                  # Docker 镜像定义
├── docker-compose.yml          # 容器编排配置
├── .dockerignore               # Docker 构建排除
├── .env.example                # 环境变量模板
├── config.yaml                 # 默认配置
├── pyproject.toml              # 项目依赖
├── src/
│   ├── main.py                 # CLI 一次性入口（debate 命令）
│   ├── cli.py                  # 交互式入口（debate-interactive 命令）
│   ├── schemas/                # Pydantic models
│   │   ├── agents.py           # Agent 响应格式
│   │   ├── arguments.py        # 论点/反驳/事实检查
│   │   ├── config.py           # 配置 schema
│   │   ├── debate.py           # 辩论状态与元数据
│   │   └── report.py           # 决策报告格式
│   ├── graph/                  # LangGraph 编排
│   │   ├── builder.py          # 状态图构建
│   │   ├── conditions.py       # 收敛判定逻辑
│   │   └── nodes/              # 各节点函数
│   ├── agents/                 # Agent 实现
│   │   ├── base.py             # BaseAgent 基类
│   │   ├── advocate.py         # 正方论证者
│   │   ├── critic.py           # 反方批评者
│   │   ├── fact_checker.py     # 事实校验者
│   │   └── moderator.py        # 主持人
│   ├── prompts/                # Prompt 模板
│   ├── llm/                    # LLM 路由层
│   │   ├── factory.py          # 模型工厂
│   │   ├── router.py           # 模型路由器
│   │   └── cost.py             # 成本计算
│   ├── core/                   # 核心业务逻辑
│   │   ├── argument_registry.py # 论点生命周期管理
│   │   └── transcript_manager.py # 辩论历史压缩
│   ├── output/                 # 输出渲染
│   │   ├── stream.py           # 实时流式输出（Rich 增强）
│   │   └── renderer.py         # Markdown 报告渲染
│   └── templates/              # Jinja2 模板
├── examples/                   # 使用示例
│   ├── java_to_go.py           # 决策示例
│   └── build_vs_buy.py         # 决策示例
└── tests/                      # 测试用例
```

## 测试

```bash
pip install -e ".[dev]"
pytest
```

## 高级用法

### 程序化调用

在自己的 Python 代码中集成辩论引擎：

```python
import asyncio
from src.main import run_debate, load_config

async def main():
    config = load_config("config.yaml")
    state = await run_debate(
        question="我们应该迁移到微服务架构吗？",
        context="团队 30 人，当前单体应用 100 万行代码",
        config=config
    )
    
    # 访问结果
    print(f"状态: {state.status.value}")
    print(f"轮数: {len(state.rounds)}")
    print(f"报告: {state.final_report.executive_summary}")

asyncio.run(main())
```

### 混合 Provider 模式

在 `config.yaml` 中为不同 Agent 指定不同模型：

```yaml
agents:
  advocate:
    provider: claude
    model: claude-sonnet-4-20250514
  critic:
    provider: openai
    model: gpt-4o
  fact_checker:
    provider: openai
    model: gpt-4o-mini  # 成本优化
  moderator:
    provider: claude
    model: claude-haiku-4-5-20251001  # 速度优化
```

### 访问详细辩论历史

```python
from src.core.argument_registry import ArgumentRegistry

# 从最终状态获取所有论点
registry = state.argument_registry
active_args = registry.get('active', [])
rebutted_args = registry.get('rebutted', [])

# 查看论点生命周期
for arg_id, record in registry.items():
    print(f"{arg_id}: {record.argument.claim}")
    print(f"  提出于: 第 {record.raised_in_round} 轮")
    print(f"  反驳数: {len(record.rebuttals)}")
    print(f"  检查数: {len(record.fact_checks)}")
```

---

## 常见问题

### Q: 如何修改辩论轮数或收敛阈值？

**A:** 编辑 `config.yaml` 的 `debate` 部分：
```yaml
debate:
  max_rounds: 10          # 增加最大轮数
  convergence_threshold: 3  # 增加收敛阈值（更难收敛）
  convergence_score_target: 0.9  # 提高收敛分数目标
```

### Q: Docker 启动后输入问题但没有反应？

**A:** 确保：
1. Docker Desktop 正在运行
2. `.env` 文件存在且包含有效的 API Key
3. `docker compose build` 成功完成
4. 尝试 Ctrl+C 中断后重新运行

### Q: 支持本地离线运行吗？

**A:** 不支持。系统需要调用 LLM API（Claude/GPT/Gemini）进行 Agent 推理。

### Q: 如何节省 LLM 成本？

**A:** 多个策略：
1. 为不同 Agent 使用不同模型（`config.yaml` 混合模式）
2. 降低 Fact-Checker 的模型版本（gpt-4o-mini 代替 gpt-4o）
3. 减少 `max_rounds`（配置中修改）
4. 使用 cheaper providers（Gemini Flash 代替 Claude Sonnet）

### Q: 支持其他 LLM Provider 吗？

**A:** 当前支持 Claude、OpenAI、Google Gemini。如需添加其他 Provider：
1. 在 `src/llm/factory.py` 添加模型创建逻辑
2. 在 `config.yaml` 中定义新 provider
3. 参考 `langchain` 官方文档添加对应的 `BaseChatModel` 实现

---

## 性能指标

典型辩论的成本和时间：

| 场景 | 轮数 | 模型 | 耗时 | 成本 |
|------|------|------|------|------|
| 简单决策 | 3 | Claude Sonnet | ~3-5 分钟 | $0.15-0.25 |
| 复杂决策 | 5 | Claude Sonnet | ~5-10 分钟 | $0.30-0.50 |
| 成本优化 | 5 | 混合模型 | ~5-10 分钟 | $0.10-0.20 |

---

## 许可证

本项目遵循 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

