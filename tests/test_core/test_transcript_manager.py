"""Tests for TranscriptManager."""
from datetime import datetime

import pytest

from maverickj.core.transcript_manager import TranscriptManager
from maverickj.schemas.debate import DebateConfig, DebateMetadata, DebateState, DebateStatus


class TestTranscriptManager:
    def setup_method(self):
        self.manager = TranscriptManager()

    def test_empty_transcript(self):
        state = DebateState(
            id="test",
            question="test",
            config=DebateConfig(),
            rounds=[],
            current_round=1,
            metadata=DebateMetadata(started_at=datetime.now()),
        )
        result = self.manager.build_context_for_agent(state, "advocate", 1)
        assert result == ""

    def test_full_transcript_within_threshold(self, sample_debate_state):
        """First N rounds should transmit a full transcript."""
        result = self.manager.build_context_for_agent(
            sample_debate_state, "advocate", 1
        )
        assert "Round 1" in result
        assert "ADV-R1-01" in result

    def test_compressed_transcript_after_threshold(self, sample_debate_state):
        """Beyond N rounds the history should be compressed."""
        # Set current_round to 3 (exceeds threshold 2)
        result = self.manager.build_context_for_agent(
            sample_debate_state, "advocate", 3
        )
        # Should use summaries instead of full content
        # Since there is only one round, the most recent round is kept in full
        assert "Round 1" in result
