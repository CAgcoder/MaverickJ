"""Regression: LLM JSON arrays with stray ASCII quotes inside Chinese strings."""

from maverickj.schemas.agents import AgentResponse, _parse_json_array_string_with_fence_strip


def test_parse_arguments_array_with_stray_quotes_in_reasoning():
    # Mirrors production failure: 严重度为"高"， — unescaped " inside JSON string value
    raw = (
        '[{"id":"RISK-R1-01","claim":"c","reasoning":"TC-014 确认严重度为"高"，自 2026",'
        '"evidence":"e","status":"active","tool_call_ids":["TC-014"]}]'
    )
    parsed = _parse_json_array_string_with_fence_strip(raw)
    assert parsed is not None
    assert len(parsed) == 1
    assert "「高」" in parsed[0]["reasoning"]


def test_agent_response_model_accepts_repaired_string_arguments():
    raw = (
        '[{"id":"RISK-R1-01","claim":"c","reasoning":"严重度为"高"，继续",'
        '"evidence":"e","status":"active","tool_call_ids":[]}]'
    )
    ar = AgentResponse(
        agent_role="critic",
        arguments=raw,  # type: ignore[arg-type]
        rebuttals=[],
        concessions=[],
    )
    assert isinstance(ar.arguments, list)
    assert ar.arguments[0].reasoning.startswith("严重度为「高」")
