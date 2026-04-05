import { z } from "zod";

// Zod schemas for validating LLM output

export const ArgumentSchema = z.object({
  id: z.string(),
  claim: z.string(),
  reasoning: z.string(),
  evidence: z.string().optional(),
  status: z.enum(["active", "rebutted", "conceded", "modified"]),
});

export const RebuttalSchema = z.object({
  targetArgumentId: z.string(),
  counterClaim: z.string(),
  reasoning: z.string(),
});

export const AgentResponseSchema = z.object({
  agentRole: z.string(),
  arguments: z.array(ArgumentSchema),
  rebuttals: z.array(RebuttalSchema),
  concessions: z.array(z.string()),
  confidenceShift: z.number().min(-1).max(1),
});

export const FactCheckSchema = z.object({
  targetArgumentId: z.string(),
  verdict: z.enum(["valid", "flawed", "needs_context", "unverifiable"]),
  explanation: z.string(),
  correction: z.string().optional(),
});

export const FactCheckResponseSchema = z.object({
  checks: z.array(FactCheckSchema),
  overallAssessment: z.string(),
});

export const ModeratorResponseSchema = z.object({
  roundSummary: z.string(),
  keyDivergences: z.array(z.string()),
  convergenceScore: z.number().min(0).max(1),
  shouldContinue: z.boolean(),
  guidanceForNextRound: z.string().optional(),
});

export const ScoredArgumentSchema = z.object({
  claim: z.string(),
  strength: z.number().min(1).max(10),
  survivedChallenges: z.number(),
  modifications: z.array(z.string()),
});

export const DecisionReportSchema = z.object({
  question: z.string(),
  executiveSummary: z.string(),
  recommendation: z.object({
    direction: z.string(),
    confidence: z.enum(["high", "medium", "low"]),
    conditions: z.array(z.string()),
  }),
  proArguments: z.array(ScoredArgumentSchema),
  conArguments: z.array(ScoredArgumentSchema),
  resolvedDisagreements: z.array(z.string()),
  unresolvedDisagreements: z.array(z.string()),
  riskFactors: z.array(z.string()),
  nextSteps: z.array(z.string()),
  debateStats: z.object({
    totalRounds: z.number(),
    argumentsRaised: z.number(),
    argumentsSurvived: z.number(),
    convergenceAchieved: z.boolean(),
  }),
});

/**
 * Extract JSON from LLM response text. Handles cases where the model
 * wraps JSON in markdown code blocks.
 */
export function extractJSON(text: string): string {
  // Try to find JSON in code blocks first
  const codeBlockMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (codeBlockMatch) {
    return codeBlockMatch[1].trim();
  }

  // Try to find raw JSON (object or array)
  const jsonMatch = text.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
  if (jsonMatch) {
    return jsonMatch[1].trim();
  }

  return text.trim();
}

/**
 * Parse and validate LLM response against a zod schema.
 */
export function parseResponse<T>(text: string, schema: z.ZodType<T>): T {
  const jsonStr = extractJSON(text);
  const parsed = JSON.parse(jsonStr);
  return schema.parse(parsed);
}
