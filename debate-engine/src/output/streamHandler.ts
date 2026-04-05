import type { AgentResponse, FactCheckResponse, ModeratorResponse, DebateRound } from "../types/index.js";

const COLORS = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  white: "\x1b[37m",
};

function c(color: keyof typeof COLORS, text: string): string {
  return `${COLORS[color]}${text}${COLORS.reset}`;
}

export function printRoundStart(round: number): void {
  console.log("");
  console.log(c("bold", `${"═".repeat(60)}`));
  console.log(c("bold", `  📢 第 ${round} 轮辩论`));
  console.log(c("bold", `${"═".repeat(60)}`));
}

export function printAgentStart(agent: string): void {
  const labels: Record<string, string> = {
    advocate: `${c("green", "🟢 正方论证者（Advocate）发言中...")}`,
    critic: `${c("red", "🔴 反方批评者（Critic）发言中...")}`,
    "fact-checker": `${c("yellow", "🟡 事实校验者（Fact-Checker）校验中...")}`,
    moderator: `${c("cyan", "🔵 主持人（Moderator）裁决中...")}`,
  };
  console.log("");
  console.log(labels[agent] || `  ${agent} 发言中...`);
}

export function printAdvocateResult(result: AgentResponse): void {
  console.log(c("green", "  ── 正方论点 ──"));
  for (const arg of result.arguments) {
    console.log(c("green", `  [${arg.id}] ${arg.claim}`));
    console.log(c("dim", `         ${arg.reasoning}`));
    if (arg.evidence) console.log(c("dim", `         📎 ${arg.evidence}`));
  }
  if (result.rebuttals.length > 0) {
    console.log(c("green", "  ── 正方反驳 ──"));
    for (const r of result.rebuttals) {
      console.log(c("green", `  ↩ ${r.targetArgumentId}: ${r.counterClaim}`));
    }
  }
  if (result.concessions.length > 0) {
    console.log(c("green", `  🤝 让步: ${result.concessions.join("; ")}`));
  }
  console.log(c("green", `  📊 信心变化: ${result.confidenceShift > 0 ? "+" : ""}${result.confidenceShift}`));
}

export function printCriticResult(result: AgentResponse): void {
  console.log(c("red", "  ── 反方论点 ──"));
  for (const arg of result.arguments) {
    console.log(c("red", `  [${arg.id}] ${arg.claim}`));
    console.log(c("dim", `         ${arg.reasoning}`));
    if (arg.evidence) console.log(c("dim", `         📎 ${arg.evidence}`));
  }
  if (result.rebuttals.length > 0) {
    console.log(c("red", "  ── 反方反驳 ──"));
    for (const r of result.rebuttals) {
      console.log(c("red", `  ↩ ${r.targetArgumentId}: ${r.counterClaim}`));
    }
  }
  if (result.concessions.length > 0) {
    console.log(c("red", `  🤝 让步: ${result.concessions.join("; ")}`));
  }
  console.log(c("red", `  📊 信心变化: ${result.confidenceShift > 0 ? "+" : ""}${result.confidenceShift}`));
}

export function printFactCheckResult(result: FactCheckResponse): void {
  console.log(c("yellow", "  ── 事实校验 ──"));
  for (const check of result.checks) {
    const icon = check.verdict === "valid" ? "✅" : check.verdict === "flawed" ? "❌" : check.verdict === "needs_context" ? "⚠️" : "❓";
    console.log(c("yellow", `  ${icon} ${check.targetArgumentId}: ${check.verdict}`));
    console.log(c("dim", `         ${check.explanation}`));
    if (check.correction) console.log(c("dim", `         💡 ${check.correction}`));
  }
  console.log(c("yellow", `  📋 ${result.overallAssessment}`));
}

export function printModeratorResult(result: ModeratorResponse): void {
  console.log(c("cyan", "  ── 主持人裁决 ──"));
  console.log(c("cyan", `  📝 ${result.roundSummary}`));
  if (result.keyDivergences.length > 0) {
    console.log(c("cyan", `  🔄 关键分歧:`));
    for (const d of result.keyDivergences) {
      console.log(c("cyan", `     • ${d}`));
    }
  }
  const bar = "█".repeat(Math.round(result.convergenceScore * 20)) + "░".repeat(20 - Math.round(result.convergenceScore * 20));
  console.log(c("cyan", `  📊 收敛分数: [${bar}] ${(result.convergenceScore * 100).toFixed(0)}%`));
  console.log(c("cyan", `  ${result.shouldContinue ? "➡️ 继续辩论" : "🏁 辩论结束"}`));
  if (result.guidanceForNextRound) {
    console.log(c("cyan", `  🎯 下轮引导: ${result.guidanceForNextRound}`));
  }
}

export function printDebateComplete(status: string, reason?: string): void {
  console.log("");
  console.log(c("bold", `${"═".repeat(60)}`));
  console.log(c("bold", `  🏁 辩论结束`));
  console.log(c("bold", `  状态: ${status}`));
  if (reason) console.log(c("bold", `  原因: ${reason}`));
  console.log(c("bold", `${"═".repeat(60)}`));
  console.log("");
}
