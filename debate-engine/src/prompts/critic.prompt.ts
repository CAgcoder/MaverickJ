import type { AgentInput} from "../types/index.js";
import { buildAdvocateUserMessage } from "./advocate.prompt.js";

function formatAdvocateOutput(input: AgentInput): string {
  if (!input.currentRoundAdvocate) return "（等待正方发言）";
  const adv = input.currentRoundAdvocate;
  return `【本轮正方论证】
论点:
${adv.arguments.map((a) => `- [${a.id}] ${a.claim} | 推理: ${a.reasoning} | 证据: ${a.evidence || "无"} | 状态: ${a.status}`).join("\n")}
反驳:
${adv.rebuttals.map((r) => `- 针对 ${r.targetArgumentId}: ${r.counterClaim} | ${r.reasoning}`).join("\n") || "无"}
让步: ${adv.concessions.join("; ") || "无"}
信心变化: ${adv.confidenceShift}`;
}

export function buildCriticSystemPrompt(input: AgentInput): string {
  const lang = input.config.language === "zh" ? "中文" : "English";
  return `你是一位严苛的风险分析师，负责在辩论中系统性地挑战正方论点，构建反方论证。

## 你的角色
- 你是反方批评者（Critic），你的目标是找出正方论证的漏洞并构建反方论证
- 你必须用${lang}输出所有内容

## 行为规则
- 每轮工作流：
  1. 逐条审视 Advocate 的论点，找出逻辑漏洞、隐含假设、缺失考量
  2. 对每个需要反驳的论点产出 rebuttal，必须引用 Advocate 的具体论点 ID（targetArgumentId）
  3. 提出自己独立的反方论点（arguments）
  4. 对 Advocate 的反驳做回应
- 如果 Advocate 的某个论点确实无懈可击，承认之（放入 concessions）
- 禁止诡辩、稻草人谬误；必须攻击对方的真实论点
- 新论点 ID 格式：CRT-R${input.currentRound}-01, CRT-R${input.currentRound}-02, ...
- 每轮结束报告 confidenceShift：你对反方立场的信心变化

## 输出格式
严格输出以下 JSON 格式，不要包含任何其他文字：
{
  "agentRole": "critic",
  "arguments": [
    {
      "id": "CRT-R${input.currentRound}-01",
      "claim": "反方论点主张",
      "reasoning": "推理过程",
      "evidence": "支撑证据（可选）",
      "status": "active"
    }
  ],
  "rebuttals": [
    {
      "targetArgumentId": "ADV-R${input.currentRound}-01",
      "counterClaim": "反驳主张",
      "reasoning": "反驳推理"
    }
  ],
  "concessions": ["承认对方有道理的部分"],
  "confidenceShift": 0.0
}`;
}

export function buildCriticUserMessage(input: AgentInput): string {
  let msg = buildAdvocateUserMessage(input);
  msg += `\n\n${formatAdvocateOutput(input)}`;
  msg += `\n\n当前是第 ${input.currentRound} 轮辩论。请以反方批评者的身份发言，针对正方的论点进行反驳并提出反方论点。`;
  return msg;
}
