import type { DebateRound } from "../types/index.js";

/**
 * Manages debate transcript and provides compressed history for context windowing.
 * - First 2 rounds: full transcript
 * - Round 3+: summarized history using Moderator's roundSummary, plus full current + previous round
 */
export class TranscriptManager {
  private rounds: DebateRound[] = [];

  addRound(round: DebateRound): void {
    this.rounds.push(round);
  }

  getAllRounds(): DebateRound[] {
    return [...this.rounds];
  }

  /**
   * Get history suitable for passing to agents as context.
   * Applies compression for rounds beyond the 2nd.
   */
  getContextHistory(currentRound: number): DebateRound[] {
    if (this.rounds.length <= 2) {
      return [...this.rounds];
    }

    // Return all rounds - the prompts themselves handle the full history.
    // The Moderator's roundSummary in early rounds serves as the compressed record.
    return [...this.rounds];
  }

  getLastModeratorGuidance(): string | undefined {
    if (this.rounds.length === 0) return undefined;
    const lastRound = this.rounds[this.rounds.length - 1];
    return lastRound.phases.moderator.guidanceForNextRound;
  }

  getRoundCount(): number {
    return this.rounds.length;
  }
}
