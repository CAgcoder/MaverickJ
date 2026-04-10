from maverickj.schemas.debate import DebateState, DebateRound


class TranscriptManager:
    """Manages compression and construction of the debate transcript."""

    def build_context_for_agent(
        self,
        state: DebateState,
        agent_role: str,
        current_round: int,
    ) -> str:
        """Build appropriate context for the specified agent."""
        if current_round <= state.config.transcript_compression_after_round:
            # First N rounds: pass the full transcript
            return self._full_transcript(state.rounds)
        else:
            # After that: replace older rounds with moderator summaries
            parts = []
            for r in state.rounds[:-1]:
                parts.append(
                    f"[Round {r.round_number} Summary] {r.moderator.round_summary}"
                )
            # Keep the most recent round in full
            if state.rounds:
                parts.append(self._format_round_full(state.rounds[-1]))
            return "\n\n".join(parts)

    def _full_transcript(self, rounds: list[DebateRound]) -> str:
        return "\n\n".join(self._format_round_full(r) for r in rounds)

    def _format_round_full(self, r: DebateRound) -> str:
        parts = [f"=== Round {r.round_number} ==="]

        # Advocate
        parts.append("[Advocate's Arguments]")
        for a in r.advocate.arguments:
            parts.append(f"- [{a.id}] {a.claim} ({a.status.value})")
            parts.append(f"  Reasoning: {a.reasoning}")
            if a.evidence:
                parts.append(f"  Evidence: {a.evidence}")
        if r.advocate.rebuttals:
            parts.append("Rebuttals: " + "; ".join(
                f"Against {rb.target_argument_id}: {rb.counter_claim}"
                for rb in r.advocate.rebuttals
            ))
        if r.advocate.concessions:
            parts.append("Concessions: " + "; ".join(r.advocate.concessions))

        # Critic
        parts.append("[Critic's Arguments]")
        for a in r.critic.arguments:
            parts.append(f"- [{a.id}] {a.claim} ({a.status.value})")
            parts.append(f"  Reasoning: {a.reasoning}")
            if a.evidence:
                parts.append(f"  Evidence: {a.evidence}")
        if r.critic.rebuttals:
            parts.append("Rebuttals: " + "; ".join(
                f"Against {rb.target_argument_id}: {rb.counter_claim}"
                for rb in r.critic.rebuttals
            ))
        if r.critic.concessions:
            parts.append("Concessions: " + "; ".join(r.critic.concessions))

        # Fact Check
        parts.append("[Fact Check]")
        for c in r.fact_check.checks:
            parts.append(f"- {c.target_argument_id}: {c.verdict.value} - {c.explanation}")
        parts.append(f"Overall Assessment: {r.fact_check.overall_assessment}")

        # Moderator
        parts.append(f"[Moderator Summary] {r.moderator.round_summary}")
        parts.append(f"Convergence Score: {r.moderator.convergence_score}")

        return "\n".join(parts)
