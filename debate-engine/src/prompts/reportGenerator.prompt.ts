import type { DebateState } from "../types/index.js";

export function buildReportGeneratorSystemPrompt(language: "zh" | "en"): string {
  const lang = language === "zh" ? "中文" : "English";
  return `你是决策报告生成器，负责基于完整的辩论记录生成结构化决策报告。

## 你的任务
基于完整的辩论记录，生成结构化决策报告。你必须用${lang}输出。

## 要求
1. executiveSummary：用 3-5 句话概括辩论结论
2. recommendation：给出建议方向、置信度、前提条件
   - 置信度基于：正方存活论点强度 vs 反方存活论点强度
   - 如果双方势均力敌，置信度为 "low"，建议 "需要更多信息"
3. proArguments / conArguments：
   - 只包含 status 为 "active" 或 "modified" 的论点
   - 按 strength 降序排列
   - strength 评分考虑：经受了多少次反驳仍存活、Fact-Checker 的评价
4. unresolvedDisagreements：标记辩论中始终无法达成共识的核心问题
5. nextSteps：基于 unresolvedDisagreements 建议具体的后续调研行动

## 输出格式
严格输出以下 JSON 格式，不要包含任何其他文字：
{
  "question": "决策问题",
  "executiveSummary": "总结...",
  "recommendation": {
    "direction": "建议方向",
    "confidence": "high|medium|low",
    "conditions": ["前提条件1", "前提条件2"]
  },
  "proArguments": [
    {
      "claim": "论点",
      "strength": 8,
      "survivedChallenges": 3,
      "modifications": ["修正历史"]
    }
  ],
  "conArguments": [...],
  "resolvedDisagreements": ["已解决分歧1"],
  "unresolvedDisagreements": ["未解决分歧1"],
  "riskFactors": ["风险1"],
  "nextSteps": ["后续行动1"],
  "debateStats": {
    "totalRounds": 4,
    "argumentsRaised": 20,
    "argumentsSurvived": 12,
    "convergenceAchieved": true
  }
}`;
}

export function buildReportGeneratorUserMessage(state: DebateState): string {
  let msg = `## 决策问题\n${state.question}\n`;
  if (state.context) {
    msg += `\n## 补充背景\n${state.context}\n`;
  }
  msg += `\n## 完整辩论记录\n`;

  for (const round of state.rounds) {
    msg += `\n### 第 ${round.roundNumber} 轮\n`;
    
    // Advocate
    msg += `**正方论证：**\n`;
    for (const arg of round.phases.advocate.arguments) {
      msg += `- [${arg.id}] ${arg.claim}\n  推理: ${arg.reasoning}\n  证据: ${arg.evidence || "无"}\n  状态: ${arg.status}\n`;
    }
    msg += `反驳: ${round.phases.advocate.rebuttals.map((r) => `${r.targetArgumentId}: ${r.counterClaim}`).join("; ") || "无"}\n`;
    msg += `让步: ${round.phases.advocate.concessions.join("; ") || "无"}\n`;
    msg += `信心变化: ${round.phases.advocate.confidenceShift}\n\n`;

    // Critic
    msg += `**反方论证：**\n`;
    for (const arg of round.phases.critic.arguments) {
      msg += `- [${arg.id}] ${arg.claim}\n  推理: ${arg.reasoning}\n  证据: ${arg.evidence || "无"}\n  状态: ${arg.status}\n`;
    }
    msg += `反驳: ${round.phases.critic.rebuttals.map((r) => `${r.targetArgumentId}: ${r.counterClaim}`).join("; ") || "无"}\n`;
    msg += `让步: ${round.phases.critic.concessions.join("; ") || "无"}\n`;
    msg += `信心变化: ${round.phases.critic.confidenceShift}\n\n`;

    // Fact Check
    msg += `**事实校验：**\n`;
    for (const check of round.phases.factCheck.checks) {
      msg += `- ${check.targetArgumentId}: ${check.verdict} — ${check.explanation}\n`;
      if (check.correction) msg += `  修正: ${check.correction}\n`;
    }
    msg += `总体评估: ${round.phases.factCheck.overallAssessment}\n\n`;

    // Moderator
    msg += `**主持人裁决：**\n`;
    msg += `总结: ${round.phases.moderator.roundSummary}\n`;
    msg += `关键分歧: ${round.phases.moderator.keyDivergences.join("; ")}\n`;
    msg += `收敛分数: ${round.phases.moderator.convergenceScore}\n`;
    msg += `是否继续: ${round.phases.moderator.shouldContinue}\n`;
    if (round.phases.moderator.guidanceForNextRound) {
      msg += `下轮引导: ${round.phases.moderator.guidanceForNextRound}\n`;
    }
  }

  msg += `\n## 辩论终止状态: ${state.status}`;
  if (state.convergenceReason) {
    msg += `\n收敛原因: ${state.convergenceReason}`;
  }
  msg += `\n总 LLM 调用: ${state.metadata.totalLLMCalls}`;
  msg += `\n总 token 消耗: ${state.metadata.totalTokensUsed}`;

  msg += `\n\n请基于以上辩论记录生成决策报告。`;
  return msg;
}
