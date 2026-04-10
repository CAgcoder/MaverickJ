"""测试 TranscriptManager"""
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
        """前 N 轮应当传完整 transcript"""
        result = self.manager.build_context_for_agent(
            sample_debate_state, "advocate", 1
        )
        assert "第 1 轮" in result
        assert "ADV-R1-01" in result

    def test_compressed_transcript_after_threshold(self, sample_debate_state):
        """超过 N 轮应当压缩历史"""
        # 把 current_round 设到 3（超过 threshold 2）
        result = self.manager.build_context_for_agent(
            sample_debate_state, "advocate", 3
        )
        # 应该使用摘要而非完整内容
        # 由于只有一轮，最近一轮保留完整
        assert "第 1 轮" in result
