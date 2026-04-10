from maverickj.schemas.debate import DebateState, DebateRound


class TranscriptManager:
    """管理辩论 transcript 的压缩与构造"""

    def build_context_for_agent(
        self,
        state: DebateState,
        agent_role: str,
        current_round: int,
    ) -> str:
        """为指定 Agent 构造合适的上下文"""
        if current_round <= state.config.transcript_compression_after_round:
            # 前 N 轮：传完整 transcript
            return self._full_transcript(state.rounds)
        else:
            # 之后：历史轮次用 Moderator 的 round_summary 替代
            parts = []
            for r in state.rounds[:-1]:
                parts.append(
                    f"[第 {r.round_number} 轮摘要] {r.moderator.round_summary}"
                )
            # 最近一轮保留完整内容
            if state.rounds:
                parts.append(self._format_round_full(state.rounds[-1]))
            return "\n\n".join(parts)

    def _full_transcript(self, rounds: list[DebateRound]) -> str:
        return "\n\n".join(self._format_round_full(r) for r in rounds)

    def _format_round_full(self, r: DebateRound) -> str:
        parts = [f"=== 第 {r.round_number} 轮 ==="]

        # Advocate
        parts.append("【正方论证】")
        for a in r.advocate.arguments:
            parts.append(f"- [{a.id}] {a.claim} ({a.status.value})")
            parts.append(f"  推理: {a.reasoning}")
            if a.evidence:
                parts.append(f"  证据: {a.evidence}")
        if r.advocate.rebuttals:
            parts.append("反驳: " + "; ".join(
                f"针对{rb.target_argument_id}: {rb.counter_claim}"
                for rb in r.advocate.rebuttals
            ))
        if r.advocate.concessions:
            parts.append("让步: " + "; ".join(r.advocate.concessions))

        # Critic
        parts.append("【反方论证】")
        for a in r.critic.arguments:
            parts.append(f"- [{a.id}] {a.claim} ({a.status.value})")
            parts.append(f"  推理: {a.reasoning}")
            if a.evidence:
                parts.append(f"  证据: {a.evidence}")
        if r.critic.rebuttals:
            parts.append("反驳: " + "; ".join(
                f"针对{rb.target_argument_id}: {rb.counter_claim}"
                for rb in r.critic.rebuttals
            ))
        if r.critic.concessions:
            parts.append("让步: " + "; ".join(r.critic.concessions))

        # Fact Check
        parts.append("【事实校验】")
        for c in r.fact_check.checks:
            parts.append(f"- {c.target_argument_id}: {c.verdict.value} - {c.explanation}")
        parts.append(f"总体评估: {r.fact_check.overall_assessment}")

        # Moderator
        parts.append(f"【主持人总结】{r.moderator.round_summary}")
        parts.append(f"收敛分数: {r.moderator.convergence_score}")

        return "\n".join(parts)
