"""
maverickj MCP Server — exposes the debate engine as MCP tools.

Install and run
---------------
::

    pip install "maverickj[mcp]"
    maverickj-mcp                     # stdio transport (default, for Claude Desktop)
    maverickj-mcp --transport sse     # SSE transport

Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json)::

    {
      "mcpServers": {
        "maverickj": {
          "command": "maverickj-mcp",
          "env": {
            "ANTHROPIC_API_KEY": "sk-ant-...",
            "DEBATE_CONFIG_PATH": "/path/to/config.yaml"
          }
        }
      }
    }

Available tools
---------------
P0 — Complete debate (single call):
  run_debate            → structured JSON decision report
  run_debate_markdown   → full Markdown report (transcript + analysis)

P1 — Step-by-step session control:
  create_debate_session → run debate, cache rounds, return session_id
  run_debate_round      → expose next round from cached session
  get_debate_status     → show session state and progress
  finalize_debate       → return final report from cached session
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "MCP extra is required. Install with: pip install 'maverickj[mcp]'"
    ) from e

from maverickj.engine import DebateEngine, DebateResult
from maverickj.main import load_config
from maverickj.schemas.debate import DebateState

mcp = FastMCP(
    "maverickj-debate",
    instructions=(
        "Multi-agent adversarial debate engine. "
        "Use run_debate or run_debate_markdown for a complete decision report. "
        "Use create_debate_session + run_debate_round for step-by-step round control."
    ),
)

# ── In-memory session store (process-lifetime, MCP server is long-running) ──
_sessions: dict[str, DebateState] = {}
_session_round_index: dict[str, int] = {}


def _get_engine(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_rounds: Optional[int] = None,
) -> DebateEngine:
    config_path = os.environ.get("DEBATE_CONFIG_PATH", "config.yaml")
    return DebateEngine(
        config=load_config(config_path),
        provider=provider or None,
        model=model or None,
        max_rounds=max_rounds or None,
        on_event=None,  # MCP: silent mode, no Rich terminal output
    )


# ──────────────────────────────────────────────────
# P0 Tools: complete debate in a single call
# ──────────────────────────────────────────────────


@mcp.tool()
async def run_debate(
    question: str,
    context: str = "",
    max_rounds: int = 0,
    provider: str = "",
    model: str = "",
) -> str:
    """Run a full multi-agent debate and return a structured JSON decision report.

    Args:
        question:   The decision question to debate (e.g. "Should we adopt microservices?")
        context:    Optional background information (team size, budget, constraints, etc.)
        max_rounds: Max debate rounds (0 = use config default)
        provider:   LLM provider override: "claude", "openai", or "gemini" (empty = config default)
        model:      LLM model override (empty = config default)

    Returns:
        JSON string with keys: question, executive_summary, recommendation,
        pro_arguments, con_arguments, risk_factors, next_steps, debate_stats
    """
    engine = _get_engine(
        provider=provider or None,
        model=model or None,
        max_rounds=max_rounds or None,
    )
    result: DebateResult = await engine.debate(
        question=question,
        context=context or None,
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool()
async def run_debate_markdown(
    question: str,
    context: str = "",
    max_rounds: int = 0,
    provider: str = "",
    model: str = "",
) -> str:
    """Run a full multi-agent debate and return a complete Markdown report.

    The report includes two parts:
    1. Complete debate transcript (all rounds, arguments, rebuttals, fact-checks)
    2. Decision analysis (executive summary, recommendation, pros/cons, risks, next steps)

    Args:
        question:   The decision question to debate
        context:    Optional background information
        max_rounds: Max debate rounds (0 = use config default)
        provider:   LLM provider override: "claude", "openai", or "gemini" (empty = config default)
        model:      LLM model override (empty = config default)

    Returns:
        Full Markdown-formatted debate report
    """
    engine = _get_engine(
        provider=provider or None,
        model=model or None,
        max_rounds=max_rounds or None,
    )
    result: DebateResult = await engine.debate(
        question=question,
        context=context or None,
    )
    return result.to_markdown()


# ──────────────────────────────────────────────────
# P1 Tools: session-based step-by-step control
# ──────────────────────────────────────────────────


@mcp.tool()
async def create_debate_session(
    question: str,
    context: str = "",
    max_rounds: int = 0,
    provider: str = "",
    model: str = "",
) -> str:
    """Create a debate session: runs the full debate internally, caches results.

    After calling this, use run_debate_round to walk through each round one-by-one,
    get_debate_status to inspect progress, and finalize_debate to get the final report.

    Args:
        question:   The decision question
        context:    Optional background information
        max_rounds: Max debate rounds (0 = use config default)
        provider:   LLM provider override (empty = config default)
        model:      LLM model override (empty = config default)

    Returns:
        JSON with session_id, total_rounds, and question
    """
    engine = _get_engine(
        provider=provider or None,
        model=model or None,
        max_rounds=max_rounds or None,
    )
    result: DebateResult = await engine.debate(
        question=question,
        context=context or None,
    )

    session_id = str(uuid.uuid4())
    _sessions[session_id] = result.state
    _session_round_index[session_id] = 0

    return json.dumps({
        "session_id": session_id,
        "question": question,
        "total_rounds": len(result.state.rounds),
        "status": result.state.status.value,
        "message": "Session created. Call run_debate_round to step through each round.",
    }, ensure_ascii=False)


@mcp.tool()
async def run_debate_round(session_id: str) -> str:
    """Advance to and return the next round from a cached debate session.

    Args:
        session_id: Session ID returned by create_debate_session

    Returns:
        JSON with the round data (advocate / critic / fact_check / moderator),
        or a message when all rounds have been exhausted.
    """
    if session_id not in _sessions:
        return json.dumps({"error": f"Session '{session_id}' not found."})

    state = _sessions[session_id]
    idx = _session_round_index[session_id]

    if idx >= len(state.rounds):
        return json.dumps({
            "message": "All rounds complete. Call finalize_debate to get the final report.",
            "total_rounds": len(state.rounds),
        })

    round_data = state.rounds[idx]
    _session_round_index[session_id] = idx + 1

    def _safe_dict(obj) -> dict:
        return obj.model_dump() if hasattr(obj, "model_dump") else {}

    return json.dumps({
        "round_number": round_data.round_number,
        "advocate": _safe_dict(round_data.advocate),
        "critic": _safe_dict(round_data.critic),
        "fact_check": _safe_dict(round_data.fact_check),
        "moderator": _safe_dict(round_data.moderator),
        "rounds_remaining": len(state.rounds) - (idx + 1),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_debate_status(session_id: str) -> str:
    """Get the current status and progress of a debate session.

    Args:
        session_id: Session ID returned by create_debate_session

    Returns:
        JSON with session metadata: question, status, rounds played vs total, cost, etc.
    """
    if session_id not in _sessions:
        return json.dumps({"error": f"Session '{session_id}' not found."})

    state = _sessions[session_id]
    idx = _session_round_index[session_id]

    return json.dumps({
        "session_id": session_id,
        "question": state.question,
        "status": state.status.value,
        "convergence_reason": state.convergence_reason,
        "rounds_total": len(state.rounds),
        "rounds_revealed": idx,
        "rounds_remaining": len(state.rounds) - idx,
        "total_cost_usd": state.metadata.total_cost_usd,
        "total_tokens": state.metadata.total_tokens_used,
        "has_final_report": state.final_report is not None,
    }, ensure_ascii=False)


@mcp.tool()
async def finalize_debate(session_id: str) -> str:
    """Return the final decision report from a completed debate session.

    Args:
        session_id: Session ID returned by create_debate_session

    Returns:
        JSON decision report (same format as run_debate)
    """
    if session_id not in _sessions:
        return json.dumps({"error": f"Session '{session_id}' not found."})

    state = _sessions[session_id]
    if state.final_report is None:
        return json.dumps({"error": "Debate has no final report."})

    from maverickj.schemas.report import DecisionReport
    from maverickj.output.renderer import render_report_to_markdown

    report = state.final_report
    if isinstance(report, dict):
        report = DecisionReport(**report)

    return json.dumps(report.model_dump(), ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────


def main() -> None:
    """Start the MCP server (stdio transport by default)."""
    import argparse
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="maverickj MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    args = parser.parse_args()

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
