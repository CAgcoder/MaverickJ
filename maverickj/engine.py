"""
DebateEngine — 高层 Facade API。

面向第三方开发者的主入口。封装了配置加载、图构建、事件路由等内部细节，
提供简洁的 async-first 接口。

使用方式
--------
最简::

    from maverickj import DebateEngine

    engine = DebateEngine()
    result = await engine.debate("Should we build or buy?")
    print(result.report.recommendation)
    print(result.to_markdown())

带配置::

    engine = DebateEngine(
        provider="openai",
        model="gpt-4o",
        max_rounds=3,
    )

静默模式（不输出到终端，适用于集成场景）::

    engine = DebateEngine(on_event=None)

自定义事件回调::

    def my_handler(event):
        print(event.type, event.round_number)

    engine = DebateEngine(on_event=my_handler)

从 YAML 加载::

    engine = DebateEngine.from_yaml("my_config.yaml")
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from maverickj.events import EventCallback
from maverickj.main import load_config, run_debate, _SENTINEL
from maverickj.output.renderer import render_report_to_markdown
from maverickj.schemas.config import DebateEngineConfig
from maverickj.schemas.debate import DebateState
from maverickj.schemas.report import DecisionReport


@dataclass
class DebateResult:
    """Debate 执行结果。包含最终报告和完整的辩论状态。"""

    state: DebateState
    report: DecisionReport

    def to_markdown(self) -> str:
        """渲染为 Markdown 格式的完整辩论报告。"""
        return render_report_to_markdown(self.report, self.state)

    def to_dict(self) -> dict:
        """将报告序列化为字典（可安全 JSON 序列化）。"""
        return self.report.model_dump()


class DebateEngine:
    """多 Agent 辩论式决策引擎的高层 Facade。

    Args:
        config:     直接传入 DebateEngineConfig 实例（与其他参数互斥）
        provider:   默认 LLM 提供商，如 "claude" / "openai" / "gemini"
        model:      默认模型名称
        max_rounds: 最大辩论轮数（覆盖 config 中的 debate.max_rounds）
        on_event:   事件回调：
                    - 不传（默认）→ Rich 终端输出
                    - None        → 静默模式
                    - callable    → 自定义处理，不触发 Rich 输出
    """

    def __init__(
        self,
        *,
        config: Optional[DebateEngineConfig] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_rounds: Optional[int] = None,
        on_event: Optional[EventCallback] = _SENTINEL,  # type: ignore[assignment]
    ) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = load_config()

        # Override individual fields if provided
        if provider is not None:
            self._config = self._config.model_copy(
                update={"default_provider": provider}
            )
        if model is not None:
            self._config = self._config.model_copy(
                update={"default_model": model}
            )
        if max_rounds is not None:
            updated_debate = self._config.debate.model_copy(
                update={"max_rounds": max_rounds}
            )
            self._config = self._config.model_copy(
                update={"debate": updated_debate}
            )

        self._on_event = on_event

    @classmethod
    def from_yaml(cls, config_path: str, **kwargs) -> "DebateEngine":
        """从 YAML 文件创建 DebateEngine 实例。

        Args:
            config_path: YAML 配置文件路径
            **kwargs:    其余参数透传给 DebateEngine.__init__
        """
        config = load_config(config_path)
        return cls(config=config, **kwargs)

    async def debate(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> DebateResult:
        """执行一场完整的辩论并返回结构化结果。

        Args:
            question: 决策问题，如 "我们应该迁移到微服务吗？"
            context:  可选背景信息（团队规模、预算、约束等）

        Returns:
            DebateResult，包含 .report (DecisionReport) 和 .state (DebateState)
        """
        state = await run_debate(
            question=question,
            config=self._config,
            context=context,
            on_event=self._on_event,
        )

        report = state.final_report
        if report is None:
            raise RuntimeError("Debate completed without generating a final report.")
        if isinstance(report, dict):
            report = DecisionReport(**report)

        return DebateResult(state=state, report=report)
