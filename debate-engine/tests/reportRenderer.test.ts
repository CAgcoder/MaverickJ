import { describe, it, expect } from "vitest";
import { renderReportToMarkdown } from "../src/output/reportRenderer.js";
import type { DecisionReport } from "../src/types/index.js";

describe("renderReportToMarkdown", () => {
  const mockReport: DecisionReport = {
    question: "Should we adopt TypeScript?",
    executiveSummary: "After thorough debate, TypeScript adoption is recommended.",
    recommendation: {
      direction: "Adopt TypeScript gradually",
      confidence: "high",
      conditions: ["Team training completed", "Migration plan approved"],
    },
    proArguments: [
      {
        claim: "Type safety reduces bugs",
        strength: 8,
        survivedChallenges: 3,
        modifications: ["Refined to focus on runtime safety"],
      },
    ],
    conArguments: [
      {
        claim: "Learning curve is steep",
        strength: 5,
        survivedChallenges: 1,
        modifications: [],
      },
    ],
    resolvedDisagreements: ["Both sides agree on gradual migration"],
    unresolvedDisagreements: ["Pace of migration remains debated"],
    riskFactors: ["Team productivity may dip temporarily"],
    nextSteps: ["Run a pilot project", "Survey team readiness"],
    debateStats: {
      totalRounds: 4,
      argumentsRaised: 15,
      argumentsSurvived: 8,
      convergenceAchieved: true,
    },
  };

  it("should generate valid markdown", () => {
    const md = renderReportToMarkdown(mockReport);
    expect(md).toContain("# 决策分析报告");
    expect(md).toContain("Should we adopt TypeScript?");
    expect(md).toContain("Adopt TypeScript gradually");
    expect(md).toContain("Type safety reduces bugs");
    expect(md).toContain("Learning curve is steep");
    expect(md).toContain("8/10");
    expect(md).toContain("5/10");
  });

  it("should include debate stats", () => {
    const md = renderReportToMarkdown(mockReport);
    expect(md).toContain("4");
    expect(md).toContain("15");
    expect(md).toContain("8");
    expect(md).toContain("是 ✅");
  });
});
