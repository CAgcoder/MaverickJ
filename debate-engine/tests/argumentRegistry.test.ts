import { describe, it, expect } from "vitest";
import { ArgumentRegistry } from "../src/orchestrator/argumentRegistry.js";
import type { Argument, FactCheck, Rebuttal } from "../src/types/index.js";

describe("ArgumentRegistry", () => {
  function createArg(id: string, claim: string): Argument {
    return { id, claim, reasoning: "test reasoning", status: "active" };
  }

  it("should register and retrieve arguments", () => {
    const registry = new ArgumentRegistry();
    const arg = createArg("ADV-R1-01", "Test claim");
    registry.register(arg, 1, "advocate");

    const active = registry.getActiveArguments();
    expect(active).toHaveLength(1);
    expect(active[0].id).toBe("ADV-R1-01");
  });

  it("should filter by agent", () => {
    const registry = new ArgumentRegistry();
    registry.register(createArg("ADV-R1-01", "Pro claim"), 1, "advocate");
    registry.register(createArg("CRT-R1-01", "Con claim"), 1, "critic");

    expect(registry.getActiveByAgent("advocate")).toHaveLength(1);
    expect(registry.getActiveByAgent("critic")).toHaveLength(1);
    expect(registry.getActiveByAgent("advocate")[0].id).toBe("ADV-R1-01");
  });

  it("should update argument status", () => {
    const registry = new ArgumentRegistry();
    registry.register(createArg("ADV-R1-01", "Test"), 1, "advocate");

    registry.updateStatus("ADV-R1-01", "rebutted");
    const active = registry.getActiveArguments();
    expect(active).toHaveLength(0);
  });

  it("should track rebuttals", () => {
    const registry = new ArgumentRegistry();
    registry.register(createArg("ADV-R1-01", "Test"), 1, "advocate");

    const rebuttal: Rebuttal = {
      targetArgumentId: "ADV-R1-01",
      counterClaim: "Counter",
      reasoning: "Because",
    };
    registry.addRebuttal("ADV-R1-01", rebuttal);

    expect(registry.getChallengeCount("ADV-R1-01")).toBe(1);
  });

  it("should mark flawed arguments from fact checks", () => {
    const registry = new ArgumentRegistry();
    registry.register(createArg("ADV-R1-01", "Flawed claim"), 1, "advocate");

    const check: FactCheck = {
      targetArgumentId: "ADV-R1-01",
      verdict: "flawed",
      explanation: "Logic error",
    };
    registry.addFactCheck("ADV-R1-01", check);

    expect(registry.getActiveArguments()).toHaveLength(0);
    expect(registry.getSurvivorStats().rebutted).toBe(1);
  });

  it("should compute survivor stats", () => {
    const registry = new ArgumentRegistry();
    registry.register(createArg("ADV-R1-01", "Active"), 1, "advocate");
    registry.register(createArg("ADV-R1-02", "Will be rebutted"), 1, "advocate");
    registry.register(createArg("CRT-R1-01", "Will be conceded"), 1, "critic");

    registry.updateStatus("ADV-R1-02", "rebutted");
    registry.updateStatus("CRT-R1-01", "conceded");

    const stats = registry.getSurvivorStats();
    expect(stats.total).toBe(3);
    expect(stats.survived).toBe(1);
    expect(stats.rebutted).toBe(1);
    expect(stats.conceded).toBe(1);
  });
});
