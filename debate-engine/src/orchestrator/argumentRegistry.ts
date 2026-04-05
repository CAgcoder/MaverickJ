import type { Argument, FactCheck, Rebuttal } from "../types/index.js";

interface TrackedArgument {
  argument: Argument;
  raisedInRound: number;
  raisedBy: "advocate" | "critic";
  rebuttals: Rebuttal[];
  factChecks: FactCheck[];
}

export class ArgumentRegistry {
  private arguments: Map<string, TrackedArgument> = new Map();

  register(arg: Argument, round: number, agent: "advocate" | "critic"): void {
    this.arguments.set(arg.id, {
      argument: { ...arg },
      raisedInRound: round,
      raisedBy: agent,
      rebuttals: [],
      factChecks: [],
    });
  }

  addRebuttal(targetId: string, rebuttal: Rebuttal): void {
    const tracked = this.arguments.get(targetId);
    if (tracked) {
      tracked.rebuttals.push(rebuttal);
    }
  }

  addFactCheck(targetId: string, check: FactCheck): void {
    const tracked = this.arguments.get(targetId);
    if (tracked) {
      tracked.factChecks.push(check);
      if (check.verdict === "flawed") {
        tracked.argument.status = "rebutted";
      }
    }
  }

  updateStatus(argId: string, status: Argument["status"]): void {
    const tracked = this.arguments.get(argId);
    if (tracked) {
      tracked.argument.status = status;
    }
  }

  getActiveArguments(): Argument[] {
    return Array.from(this.arguments.values())
      .filter((t) => t.argument.status === "active" || t.argument.status === "modified")
      .map((t) => t.argument);
  }

  getActiveByAgent(agent: "advocate" | "critic"): Argument[] {
    return Array.from(this.arguments.values())
      .filter(
        (t) =>
          t.raisedBy === agent &&
          (t.argument.status === "active" || t.argument.status === "modified")
      )
      .map((t) => t.argument);
  }

  getAll(): TrackedArgument[] {
    return Array.from(this.arguments.values());
  }

  getSurvivorStats(): { total: number; survived: number; rebutted: number; conceded: number } {
    const all = Array.from(this.arguments.values());
    return {
      total: all.length,
      survived: all.filter(
        (t) => t.argument.status === "active" || t.argument.status === "modified"
      ).length,
      rebutted: all.filter((t) => t.argument.status === "rebutted").length,
      conceded: all.filter((t) => t.argument.status === "conceded").length,
    };
  }

  getChallengeCount(argId: string): number {
    const tracked = this.arguments.get(argId);
    if (!tracked) return 0;
    return tracked.rebuttals.length + tracked.factChecks.filter((fc) => fc.verdict === "flawed").length;
  }
}
