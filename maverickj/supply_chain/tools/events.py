from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def query_active_events(
    *,
    region: str | None = None,
    type: str | None = None,
    severity: str | None = None,
    events_path: str | None = None,
) -> list[dict[str, Any]]:
    path = Path(events_path) if events_path else Path(__file__).resolve().parent.parent / "data" / "events.json"
    events = json.loads(path.read_text(encoding="utf-8"))
    filtered = [e for e in events if e.get("active")]
    if region:
        filtered = [e for e in filtered if e.get("region") == region]
    if type:
        filtered = [e for e in filtered if e.get("type") == type]
    if severity:
        filtered = [e for e in filtered if e.get("severity") == severity]
    return filtered

