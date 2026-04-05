export interface DebateState {
  id: string;
  question: string;
  context?: string;
  config: DebateConfig;
  rounds: DebateRound[];
  status: "running" | "converged" | "max_rounds" | "error";
  convergenceReason?: string;
  finalReport?: DecisionReport;
  metadata: {
    startedAt: string;
    completedAt?: string;
    totalLLMCalls: number;
    totalTokensUsed: number;
  };
}

export interface DebateConfig {
  maxRounds: number;
  convergenceThreshold: number;
  model: string;
  temperature: number;
  language: "zh" | "en";
}

export interface DebateRound {
  roundNumber: number;
  phases: {
    advocate: AgentResponse;
    critic: AgentResponse;
    factCheck: FactCheckResponse;
    moderator: ModeratorResponse;
  };
}

export interface AgentResponse {
  agentRole: string;
  arguments: Argument[];
  rebuttals: Rebuttal[];
  concessions: string[];
  confidenceShift: number;
}

export interface Argument {
  id: string;
  claim: string;
  reasoning: string;
  evidence?: string;
  status: "active" | "rebutted" | "conceded" | "modified";
}

export interface Rebuttal {
  targetArgumentId: string;
  counterClaim: string;
  reasoning: string;
}

export interface FactCheckResponse {
  checks: FactCheck[];
  overallAssessment: string;
}

export interface FactCheck {
  targetArgumentId: string;
  verdict: "valid" | "flawed" | "needs_context" | "unverifiable";
  explanation: string;
  correction?: string;
}

export interface ModeratorResponse {
  roundSummary: string;
  keyDivergences: string[];
  convergenceScore: number;
  shouldContinue: boolean;
  guidanceForNextRound?: string;
}

export interface DecisionReport {
  question: string;
  executiveSummary: string;
  recommendation: {
    direction: string;
    confidence: "high" | "medium" | "low";
    conditions: string[];
  };
  proArguments: ScoredArgument[];
  conArguments: ScoredArgument[];
  resolvedDisagreements: string[];
  unresolvedDisagreements: string[];
  riskFactors: string[];
  nextSteps: string[];
  debateStats: {
    totalRounds: number;
    argumentsRaised: number;
    argumentsSurvived: number;
    convergenceAchieved: boolean;
  };
}

export interface ScoredArgument {
  claim: string;
  strength: number;
  survivedChallenges: number;
  modifications: string[];
}

export interface AgentInput {
  question: string;
  context?: string;
  config: DebateConfig;
  history: DebateRound[];
  currentRound: number;
  moderatorGuidance?: string;
  currentRoundAdvocate?: AgentResponse;
  currentRoundCritic?: AgentResponse;
  currentRoundFactCheck?: FactCheckResponse;
}
