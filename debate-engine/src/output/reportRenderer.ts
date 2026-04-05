import type { DecisionReport, DebateState } from "../types/index.js";

export function renderReportToMarkdown(report: DecisionReport, state?: DebateState): string {
  let md = "";

  md += `# 决策分析报告\n\n`;
  md += `## 决策问题\n\n${report.question}\n\n`;

  md += `---\n\n`;
  md += `## 执行摘要\n\n${report.executiveSummary}\n\n`;

  md += `---\n\n`;
  md += `## 建议\n\n`;
  md += `- **方向：** ${report.recommendation.direction}\n`;
  md += `- **置信度：** ${formatConfidence(report.recommendation.confidence)}\n`;
  if (report.recommendation.conditions.length > 0) {
    md += `- **前提条件：**\n`;
    for (const cond of report.recommendation.conditions) {
      md += `  - ${cond}\n`;
    }
  }
  md += `\n`;

  md += `---\n\n`;
  md += `## 正方论点（支持方）\n\n`;
  if (report.proArguments.length === 0) {
    md += `*无存活论点*\n\n`;
  } else {
    for (const arg of report.proArguments) {
      md += `### 💪 ${arg.claim}\n`;
      md += `- **强度：** ${renderStrength(arg.strength)}\n`;
      md += `- **经受挑战：** ${arg.survivedChallenges} 次\n`;
      if (arg.modifications.length > 0) {
        md += `- **修正历史：**\n`;
        for (const mod of arg.modifications) {
          md += `  - ${mod}\n`;
        }
      }
      md += `\n`;
    }
  }

  md += `---\n\n`;
  md += `## 反方论点（反对方）\n\n`;
  if (report.conArguments.length === 0) {
    md += `*无存活论点*\n\n`;
  } else {
    for (const arg of report.conArguments) {
      md += `### ⚠️ ${arg.claim}\n`;
      md += `- **强度：** ${renderStrength(arg.strength)}\n`;
      md += `- **经受挑战：** ${arg.survivedChallenges} 次\n`;
      if (arg.modifications.length > 0) {
        md += `- **修正历史：**\n`;
        for (const mod of arg.modifications) {
          md += `  - ${mod}\n`;
        }
      }
      md += `\n`;
    }
  }

  if (report.resolvedDisagreements.length > 0) {
    md += `---\n\n`;
    md += `## 已解决的分歧\n\n`;
    for (const d of report.resolvedDisagreements) {
      md += `- ✅ ${d}\n`;
    }
    md += `\n`;
  }

  if (report.unresolvedDisagreements.length > 0) {
    md += `---\n\n`;
    md += `## 未解决的核心分歧\n\n`;
    for (const d of report.unresolvedDisagreements) {
      md += `- ❓ ${d}\n`;
    }
    md += `\n`;
  }

  if (report.riskFactors.length > 0) {
    md += `---\n\n`;
    md += `## 关键风险\n\n`;
    for (const risk of report.riskFactors) {
      md += `- 🔴 ${risk}\n`;
    }
    md += `\n`;
  }

  if (report.nextSteps.length > 0) {
    md += `---\n\n`;
    md += `## 建议后续行动\n\n`;
    for (let i = 0; i < report.nextSteps.length; i++) {
      md += `${i + 1}. ${report.nextSteps[i]}\n`;
    }
    md += `\n`;
  }

  md += `---\n\n`;
  md += `## 辩论统计\n\n`;
  md += `| 项目 | 数值 |\n`;
  md += `|------|------|\n`;
  md += `| 总辩论轮数 | ${report.debateStats.totalRounds} |\n`;
  md += `| 提出论点总数 | ${report.debateStats.argumentsRaised} |\n`;
  md += `| 存活论点数 | ${report.debateStats.argumentsSurvived} |\n`;
  md += `| 是否达成收敛 | ${report.debateStats.convergenceAchieved ? "是 ✅" : "否 ❌"} |\n`;

  if (state) {
    md += `| 总 LLM 调用 | ${state.metadata.totalLLMCalls} |\n`;
    md += `| 总 Token 消耗 | ${state.metadata.totalTokensUsed.toLocaleString()} |\n`;
    if (state.metadata.startedAt && state.metadata.completedAt) {
      const duration =
        (new Date(state.metadata.completedAt).getTime() - new Date(state.metadata.startedAt).getTime()) / 1000;
      md += `| 耗时 | ${duration.toFixed(1)} 秒 |\n`;
    }
  }

  return md;
}

function formatConfidence(confidence: "high" | "medium" | "low"): string {
  switch (confidence) {
    case "high":
      return "🟢 高";
    case "medium":
      return "🟡 中";
    case "low":
      return "🔴 低";
  }
}

function renderStrength(strength: number): string {
  const filled = Math.round(strength);
  const empty = 10 - filled;
  return `${"█".repeat(filled)}${"░".repeat(empty)} ${strength}/10`;
}
