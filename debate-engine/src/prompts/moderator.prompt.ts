import type { AgentInput, DebateRound } from "../types/index.js";

function formatFullTranscript(input: AgentInput): string {
  let msg = "";

  // Historical rounds
  for (const round of input.history) {
    msg += formatRound(round);
    msg += "\n\n";
  }

  // Current round phases completed so far
  msg += `=== 第 ${input.currentRound} 轮（当前轮）===\n`;
  if (input.currentRoundAdvocate) {
    const adv = input.currentRoundAdvocate;
    msg += `【正方论证】\n`;
    msg += adv.arguments.map((a) => `- [${a.id}] ${a.claim} (${a.status})`).join("\n") + "\n";
    msg += `反驳: ${adv.rebuttals.map((r) => `${r.targetArgumentId}: ${r.counterClaim}`).join("; ") || "无"}\n`;
    msg += `让步: ${adv.concessions.join("; ") || "无"}\n`;
    msg += `信心变化: ${adv.confidenceShift}\n\n`;
  }
  if (input.currentRoundCritic) {
    const crt = input.currentRoundCritic;
    msg += `【反方论证】\n`;
    msg += crt.arguments.map((a) => `- [${a.id}] ${a.claim} (${a.status})`).join("\n") + "\n";
    msg += `反驳: ${crt.rebuttals.map((r) => `${r.targetArgumentId}: ${r.counterClaim}`).join("; ") || "无"}\n`;
    msg += `让步: ${crt.concessions.join("; ") || "无"}\n`;
    msg += `信心变化: ${crt.confidenceShift}\n\n`;
  }
  if (input.currentRoundFactCheck) {
    const fc = input.currentRoundFactCheck;
    msg += `【事实校验】\n`;
    msg += fc.checks.map((c) => `- ${c.targetArgumentId}: ${c.verdict} - ${c.explanation}`).join("\n") + "\n";
    msg += `总体评估: ${fc.overallAssessment}\n\n`;
  }

  return msg;
}

function formatRound(round: DebateRound): string {
  return `=== 第 ${round.roundNumber} 轮 ===
【正方】${round.phases.advocate.arguments.map((a) => `[${a.id}] ${a.claim} (${a.status})`).join("; ")}
【反方】${round.phases.critic.arguments.map((a) => `[${a.id}] ${a.claim} (${a.status})`).join("; ")}
【校验】${round.phases.factCheck.overallAssessment}
【总结】${round.phases.moderator.roundSummary}
收敛分数: ${round.phases.moderator.convergenceScore}`;
}

export function buildModeratorSystemPrompt(input: AgentInput): string {
  const lang = input.config.language === "zh" ? "中文" : "English";
  return `你是辩论主持人（Moderator），负责控制辩论节奏、判断收敛、引导焦点。

## 你的角色
- 你是中立的辩论主持人
- 你必须用${lang}输出所有内容

## 每轮你需要完成的工作
1. 总结本轮辩论进展（roundSummary）
2. 识别当前最关键的未解决分歧（keyDivergences）
3. 计算收敛分数（convergenceScore，0-1）：
   - 双方新论点数量是否递减
   - 让步（concessions）是否增加
   - 关键分歧是否在收窄
4. 判断是否应该继续辩论（shouldContinue）
5. 如果继续，给出下一轮的焦点引导（guidanceForNextRound）

## 收敛判定规则
- convergenceScore >= 0.8 且连续 ${input.config.convergenceThreshold} 轮无实质性新论点 → shouldContinue = false
- 当前已到第 ${input.currentRound} 轮，最大轮数为 ${input.config.maxRounds}
- 如果当前轮 = 最大轮数 → shouldContinue = false
- 双方信心变化都趋于 0 → 可以考虑终止

## 输出格式
严格输出以下 JSON 格式，不要包含任何其他文字：
{
  "roundSummary": "本轮总结...",
  "keyDivergences": ["分歧1", "分歧2"],
  "convergenceScore": 0.5,
  "shouldContinue": true,
  "guidanceForNextRound": "下一轮建议聚焦于..."
}`;
}

export function buildModeratorUserMessage(input: AgentInput): string {
  let msg = `## 决策问题\n${input.question}\n`;
  if (input.context) {
    msg += `\n## 补充背景\n${input.context}\n`;
  }
  msg += `\n## 完整辩论记录\n${formatFullTranscript(input)}\n`;
  msg += `请对第 ${input.currentRound} 轮辩论做出裁决。`;
  return msg;
}
