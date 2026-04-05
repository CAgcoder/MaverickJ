import { v4 as uuidv4 } from "uuid";
import type {
  DebateState,
  DebateConfig,
  DebateRound,
  AgentInput,
  DecisionReport,
  AgentResponse,
  FactCheckResponse,
  ModeratorResponse,
} from "../types/index.js";
import { AdvocateAgent } from "../agents/advocate.js";
import { CriticAgent } from "../agents/critic.js";
import { FactCheckerAgent } from "../agents/factChecker.js";
import { ModeratorAgent } from "../agents/moderator.js";
import { ArgumentRegistry } from "./argumentRegistry.js";
import { TranscriptManager } from "./transcriptManager.js";
import { callLLM } from "../llm/client.js";
import { parseResponse, DecisionReportSchema } from "../llm/responseParser.js";
import {
  buildReportGeneratorSystemPrompt,
  buildReportGeneratorUserMessage,
} from "../prompts/reportGenerator.prompt.js";

export interface DebateCallbacks {
  onRoundStart?: (round: number) => void;
  onAgentStart?: (agent: string, round: number) => void;
  onAgentComplete?: (agent: string, round: number, result: unknown) => void;
  onRoundComplete?: (round: DebateRound) => void;
  onDebateEnd?: (state: DebateState) => void;
}

export async function runDebate(
  question: string,
  config: DebateConfig,
  context?: string,
  callbacks?: DebateCallbacks
): Promise<DebateState> {
  const state: DebateState = {
    id: uuidv4(),
    question,
    context,
    config,
    rounds: [],
    status: "running",
    metadata: {
      startedAt: new Date().toISOString(),
      totalLLMCalls: 0,
      totalTokensUsed: 0,
    },
  };

  const advocate = new AdvocateAgent();
  const critic = new CriticAgent();
  const factChecker = new FactCheckerAgent();
  const moderator = new ModeratorAgent();
  const registry = new ArgumentRegistry();
  const transcript = new TranscriptManager();

  let consecutiveNoNewArgs = 0;

  try {
    for (let round = 1; round <= config.maxRounds; round++) {
      callbacks?.onRoundStart?.(round);

      const history = transcript.getContextHistory(round);
      const moderatorGuidance = transcript.getLastModeratorGuidance();

      const baseInput: AgentInput = {
        question,
        context,
        config,
        history,
        currentRound: round,
        moderatorGuidance,
      };

      // Step 1: Advocate
      callbacks?.onAgentStart?.("advocate", round);
      const advocateResult = await executeAgentWithFallback(
        () => advocate.execute(baseInput),
        state,
        "advocate",
        round
      );
      callbacks?.onAgentComplete?.("advocate", round, advocateResult);

      // Register advocate arguments
      for (const arg of advocateResult.arguments) {
        registry.register(arg, round, "advocate");
      }
      for (const rebuttal of advocateResult.rebuttals) {
        registry.addRebuttal(rebuttal.targetArgumentId, rebuttal);
      }

      // Step 2: Critic
      callbacks?.onAgentStart?.("critic", round);
      const criticInput: AgentInput = {
        ...baseInput,
        currentRoundAdvocate: advocateResult,
      };
      const criticResult = await executeAgentWithFallback(
        () => critic.execute(criticInput),
        state,
        "critic",
        round
      );
      callbacks?.onAgentComplete?.("critic", round, criticResult);

      // Register critic arguments
      for (const arg of criticResult.arguments) {
        registry.register(arg, round, "critic");
      }
      for (const rebuttal of criticResult.rebuttals) {
        registry.addRebuttal(rebuttal.targetArgumentId, rebuttal);
      }

      // Step 3: Fact-checker
      callbacks?.onAgentStart?.("fact-checker", round);
      const factCheckInput: AgentInput = {
        ...baseInput,
        currentRoundAdvocate: advocateResult,
        currentRoundCritic: criticResult,
      };
      const factCheckResult = await executeAgentWithFallback(
        () => factChecker.execute(factCheckInput),
        state,
        "fact-checker",
        round
      );
      callbacks?.onAgentComplete?.("fact-checker", round, factCheckResult);

      // Apply fact check results
      for (const check of factCheckResult.checks) {
        registry.addFactCheck(check.targetArgumentId, check);
      }

      // Step 4: Moderator
      callbacks?.onAgentStart?.("moderator", round);
      const moderatorInput: AgentInput = {
        ...baseInput,
        currentRoundAdvocate: advocateResult,
        currentRoundCritic: criticResult,
        currentRoundFactCheck: factCheckResult,
      };
      const moderatorResult = await executeAgentWithFallback(
        () => moderator.execute(moderatorInput),
        state,
        "moderator",
        round
      );
      callbacks?.onAgentComplete?.("moderator", round, moderatorResult);

      // Build the round
      const debateRound: DebateRound = {
        roundNumber: round,
        phases: {
          advocate: advocateResult,
          critic: criticResult,
          factCheck: factCheckResult,
          moderator: moderatorResult,
        },
      };

      state.rounds.push(debateRound);
      transcript.addRound(debateRound);
      callbacks?.onRoundComplete?.(debateRound);

      // Check convergence
      const newArgsCount =
        advocateResult.arguments.filter((a) => a.status === "active").length +
        criticResult.arguments.filter((a) => a.status === "active").length;

      if (newArgsCount === 0) {
        consecutiveNoNewArgs++;
      } else {
        consecutiveNoNewArgs = 0;
      }

      // Termination conditions
      if (!moderatorResult.shouldContinue) {
        state.status = "converged";
        state.convergenceReason = `主持人判定辩论收敛 (收敛分数: ${moderatorResult.convergenceScore})`;
        break;
      }
      if (moderatorResult.convergenceScore >= 0.8 && consecutiveNoNewArgs >= config.convergenceThreshold) {
        state.status = "converged";
        state.convergenceReason = `连续 ${consecutiveNoNewArgs} 轮无新论点，收敛分数 ${moderatorResult.convergenceScore}`;
        break;
      }
      if (round === config.maxRounds) {
        state.status = "max_rounds";
        state.convergenceReason = `达到最大辩论轮数 (${config.maxRounds})`;
      }
    }

    // Generate final report
    const report = await generateReport(state);
    state.finalReport = report;
    state.metadata.completedAt = new Date().toISOString();
    state.metadata.totalLLMCalls++; // report generation call

    callbacks?.onDebateEnd?.(state);
    return state;
  } catch (error) {
    state.status = "error";
    state.metadata.completedAt = new Date().toISOString();
    throw error;
  }
}

async function executeAgentWithFallback<T>(
  executor: () => Promise<{ result: T; metrics: { inputTokens: number; outputTokens: number } }>,
  state: DebateState,
  agentName: string,
  _round: number
): Promise<T> {
  try {
    const { result, metrics } = await executor();
    state.metadata.totalLLMCalls++;
    state.metadata.totalTokensUsed += metrics.inputTokens + metrics.outputTokens;
    return result;
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[${agentName}] 第 ${_round} 轮执行失败: ${msg}`);
    throw error;
  }
}

async function generateReport(state: DebateState): Promise<DecisionReport> {
  const systemPrompt = buildReportGeneratorSystemPrompt(state.config.language);
  const userMessage = buildReportGeneratorUserMessage(state);

  const result = await callLLM(systemPrompt, [{ role: "user", content: userMessage }], state.config.model, state.config.temperature);
  state.metadata.totalTokensUsed += result.inputTokens + result.outputTokens;

  return parseResponse(result.content, DecisionReportSchema);
}
