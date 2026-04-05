import type { AgentInput, DebateRound } from "../types/index.js";

function formatHistory(rounds: DebateRound[]): string {
  if (rounds.length === 0) return "（尚无历史辩论记录）";
  return rounds
    .map((r) => {
      return `=== 第 ${r.roundNumber} 轮 ===
【正方论证】
${r.phases.advocate.arguments.map((a) => `- [${a.id}] ${a.claim} (${a.status})`).join("\n")}
反驳: ${r.phases.advocate.rebuttals.map((rb) => `针对${rb.targetArgumentId}: ${rb.counterClaim}`).join("; ") || "无"}
让步: ${r.phases.advocate.concessions.join("; ") || "无"}
信心变化: ${r.phases.advocate.confidenceShift}

【反方批评】
${r.phases.critic.arguments.map((a) => `- [${a.id}] ${a.claim} (${a.status})`).join("\n")}
反驳: ${r.phases.critic.rebuttals.map((rb) => `针对${rb.targetArgumentId}: ${rb.counterClaim}`).join("; ") || "无"}
让步: ${r.phases.critic.concessions.join("; ") || "无"}
信心变化: ${r.phases.critic.confidenceShift}

【事实校验】
${r.phases.factCheck.checks.map((c) => `- ${c.targetArgumentId}: ${c.verdict} - ${c.explanation}`).join("\n")}
总体评估: ${r.phases.factCheck.overallAssessment}

【主持人总结】
${r.phases.moderator.roundSummary}
关键分歧: ${r.phases.moderator.keyDivergences.join("; ")}
收敛分数: ${r.phases.moderator.convergenceScore}`;
    })
    .join("\n\n");
}

export function buildAdvocateSystemPrompt(input: AgentInput): string {
  const lang = input.config.language === "zh" ? "中文" : "English";
  return `你是一位资深的商业战略顾问，负责在辩论中论证正方立场（即"应该做"的方向）。

## 你的角色
- 你是正方论证者（Advocate），你的目标是为决策问题构建最强的正方论证
- 你必须用${lang}输出所有内容

## 行为规则
${input.currentRound === 1 ? `- 这是第一轮辩论，请独立提出 3-5 个核心正方论点
- 每个论点必须有清晰的主张（claim）、推理过程（reasoning）和支撑证据（evidence）
- 论点 ID 格式：ADV-R${input.currentRound}-01, ADV-R${input.currentRound}-02, ...` : `- 这是第 ${input.currentRound} 轮辩论，你已经看到了之前的辩论记录
- 你需要回应 Critic 的反驳和 Fact-Checker 的校验结果
- 对被有效反驳的论点：修正立场或承认让步（放入 concessions）
- 对被部分反驳的论点：补充论证、修正措辞（将论点状态改为 modified）
- 可以引入新论点来强化正方整体论证
- 对 Critic 的论点提出你自己的反驳（rebuttals），需引用对方论点 ID（targetArgumentId）
- 新论点 ID 格式：ADV-R${input.currentRound}-01, ADV-R${input.currentRound}-02, ...`}
- 每轮结束报告 confidenceShift：你对正方立场的信心变化（-1 到 1 之间，负数表示信心降低）
- 禁止无视对方有效反驳
- 禁止重复已被推翻的论点
- 只有当对方论证确实无懈可击时才承认让步

## 输出格式
严格输出以下 JSON 格式，不要包含任何其他文字：
{
  "agentRole": "advocate",
  "arguments": [
    {
      "id": "ADV-R${input.currentRound}-01",
      "claim": "论点主张",
      "reasoning": "推理过程",
      "evidence": "支撑证据（可选）",
      "status": "active"
    }
  ],
  "rebuttals": [
    {
      "targetArgumentId": "CRT-R1-01",
      "counterClaim": "反驳主张",
      "reasoning": "反驳推理"
    }
  ],
  "concessions": ["承认对方有道理的部分"],
  "confidenceShift": 0.0
}`;
}

export function buildAdvocateUserMessage(input: AgentInput): string {
  let msg = `## 决策问题\n${input.question}\n`;
  if (input.context) {
    msg += `\n## 补充背景\n${input.context}\n`;
  }
  msg += `\n## 辩论历史\n${formatHistory(input.history)}\n`;
  if (input.moderatorGuidance) {
    msg += `\n## 主持人引导\n${input.moderatorGuidance}\n`;
  }
  msg += `\n当前是第 ${input.currentRound} 轮辩论。请以正方论证者的身份发言。`;
  return msg;
}
