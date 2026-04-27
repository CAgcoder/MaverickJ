"""Anthropic Messages API prompt caching (request-level `cache_control`).

Mirrors the SDK shape::

    client.messages.create(
        model="...",
        max_tokens=1024,
        cache_control={"type": "ephemeral"},
        system="...",
        messages=[...],
    )

We attach the same field via ``ChatAnthropic(..., model_kwargs={"cache_control": ...})``
in :func:`maverickj.llm.factory.create_model` so every Claude call includes it.

See https://platform.claude.com/docs/en/build-with-claude/prompt-caching
"""

from __future__ import annotations

# Top-level Messages API parameter (not a content-block field).
ANTHROPIC_MESSAGES_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}
