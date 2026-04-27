"""Markdown blocks for supply-chain-only DecisionReport fields."""

from __future__ import annotations

from typing import Any

from maverickj.schemas.debate import DebateState
from maverickj.schemas.report import DecisionReport
from maverickj.supply_chain.schemas.decision import CircuitBreaker, DecisionOption


def _opt(row: Any) -> DecisionOption | None:
    if isinstance(row, DecisionOption):
        return row
    if isinstance(row, dict):
        try:
            return DecisionOption.model_validate(row)
        except Exception:
            return None
    return None


def _brk(row: Any) -> CircuitBreaker | None:
    if isinstance(row, CircuitBreaker):
        return row
    if isinstance(row, dict):
        try:
            return CircuitBreaker.model_validate(row)
        except Exception:
            return None
    return None


def render_supply_chain_extras(report: DecisionReport, state: DebateState) -> list[str]:
    """Four H2 sections: decision matrix, data evidence, minority report, circuit breakers."""
    lang_zh = state.config.language in ("zh", "auto")

    def title(a_zh: str, b_en: str) -> str:
        return f"## {a_zh}" if lang_zh else f"## {b_en}"

    lines: list[str] = []
    lines.append("")
    lines.append("---")
    lines.append("")

    # Decision matrix
    lines.append(title("决策矩阵", "Decision matrix"))
    lines.append("")
    dm = report.decision_matrix or []
    if dm:
        lines.append("| Path | Expected TCO (USD) | Impl. cost (USD) | Risk warnings | Tool refs |")
        lines.append("|------|-------------------:|-----------------:|---------------|-----------|")
        for raw in dm:
            o = _opt(raw)
            if not o:
                continue
            warns = "; ".join(o.risk_warnings) if o.risk_warnings else "—"
            refs = ", ".join(o.supporting_tool_calls) if o.supporting_tool_calls else "—"
            etco = f"{o.expected_tco_usd:,.0f}" if o.expected_tco_usd is not None else "—"
            ic = f"{o.implementation_cost_usd:,.0f}" if o.implementation_cost_usd is not None else "—"
            lines.append(f"| {o.path_name} | {etco} | {ic} | {warns} | {refs} |")
        lines.append("")
    else:
        lines.append("*—*" if lang_zh else "*No rows.*")
        lines.append("")

    # Data evidence
    lines.append(title("数据证据", "Data evidence"))
    lines.append("")
    ev = report.data_evidence or []
    if ev:
        for i, raw in enumerate(ev, 1):
            if hasattr(raw, "model_dump"):
                payload = raw.model_dump()
            elif isinstance(raw, dict):
                payload = raw
            else:
                payload = {"summary": str(raw)}
            tid = payload.get("id", f"#{i}")
            tname = payload.get("tool_name", "?")
            summ = payload.get("summary", "")
            lines.append(f"### {tid} — `{tname}`")
            lines.append("")
            lines.append(summ or "")
            outs = payload.get("outputs")
            if outs:
                lines.append("")
                lines.append(f"```json\n{_short_json(outs)}\n```")
            lines.append("")
    else:
        lines.append("*—*" if lang_zh else "*No entries.*")
        lines.append("")

    # Minority report
    lines.append(title("少数派报告", "Minority report"))
    lines.append("")
    mr = report.minority_report or []
    if mr:
        for line in mr:
            lines.append(f"- {line}")
        lines.append("")
    else:
        lines.append("*—*" if lang_zh else "*None.*")
        lines.append("")

    # Circuit breakers
    lines.append(title("黑天鹅预案", "Circuit breakers"))
    lines.append("")
    cb = report.circuit_breakers or []
    if cb:
        lines.append("| Metric | Threshold | Condition | Fallback | Rationale |")
        lines.append("|--------|-----------|-----------|----------|-----------|")
        for raw in cb:
            b = _brk(raw)
            if not b:
                continue
            lines.append(
                f"| `{b.trigger_metric}` | {b.threshold_value} | {b.trigger_condition} "
                f"| {b.fallback_action} | {b.rationale or '—'} |"
            )
        lines.append("")
    else:
        lines.append("*—*" if lang_zh else "*None.*")
        lines.append("")

    return lines


def _short_json(obj: Any, *, limit: int = 1200) -> str:
    import json

    s = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    if len(s) > limit:
        return s[: limit - 3] + "..."
    return s
