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

### 1. 安装依赖

```bash
cd debate-engine-py
pip install -e .
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入至少一个 Provider 的 API Key
```

### 3. 运行辩论

```bash
# CLI 方式
python -m src.main "我们应该将 Java 后端迁移到 Go 吗？" "50人团队，Spring Boot 3年"

# 示例脚本
python examples/java_to_go.py
python examples/build_vs_buy.py
```

## 配置

编辑 `config.yaml` 选择模型和辩论参数：

```yaml
# 统一切换模型
default_provider: claude
default_model: claude-sonnet-4-20250514

# 辩论参数
debate:
  max_rounds: 5
  convergence_threshold: 2
  convergence_score_target: 0.8
```

支持为不同 Agent 配置不同模型（混合调用模式），详见 `config.yaml` 注释。

## 项目结构

```
debate-engine-py/
├── config.yaml                 # 默认配置
├── pyproject.toml              # 项目依赖
├── src/
│   ├── main.py                 # CLI 入口
│   ├── schemas/                # Pydantic models
│   ├── graph/                  # LangGraph 编排
│   │   ├── builder.py          # 状态图构建
│   │   ├── conditions.py       # 收敛判定
│   │   └── nodes/              # 各节点函数
│   ├── agents/                 # Agent 逻辑
│   ├── prompts/                # Prompt 模板
│   ├── llm/                    # LLM 路由层
│   ├── core/                   # 核心业务逻辑
│   ├── output/                 # 输出渲染
│   └── templates/              # Jinja2 模板
├── examples/                   # 示例脚本
└── tests/                      # 测试
```

## 测试

```bash
pip install -e ".[dev]"
pytest
```
