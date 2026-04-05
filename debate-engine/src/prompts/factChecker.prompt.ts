import type { AgentInput } from "../types/index.js";

function formatCurrentRoundArguments(input: AgentInput): string {
  let msg = "";
  if (input.currentRoundAdvocate) {
    const adv = input.currentRoundAdvocate;
    msg += `【正方论证（Advocate）】\n`;
    msg += adv.arguments.map((a) => `- [${a.id}] ${a.claim}\n  推理: ${a.reasoning}\n  证据: ${a.evidence || "无"}\n  状态: ${a.status}`).join("\n");
    msg += `\n反驳: ${adv.rebuttals.map((r) => `针对${r.targetArgumentId}: ${r.counterClaim}`).join("; ") || "无"}\n`;
  }
  if (input.currentRoundCritic) {
    const crt = input.currentRoundCritic;
    msg += `\n【反方论证（Critic）】\n`;
    msg += crt.arguments.map((a) => `- [${a.id}] ${a.claim}\n  推理: ${a.reasoning}\n  证据: ${a.evidence || "无"}\n  状态: ${a.status}`).join("\n");
    msg += `\n反驳: ${crt.rebuttals.map((r) => `针对${r.targetArgumentId}: ${r.counterClaim}`).join("; ") || "无"}\n`;
  }
  return msg;
}

export function buildFactCheckerSystemPrompt(input: AgentInput): string {
  const lang = input.config.language === "zh" ? "中文" : "English";
  return `你是一位逻辑学教授，作为中立第三方审视双方论证的逻辑一致性和事实准确性。

## 你的角色
- 你是事实校验者（Fact-Checker），你不选边站，只评估论证质量
- 你必须用${lang}输出所有内容

## 行为规则
- 对本轮所有 active 状态的论点和反驳进行校验
- 对每个论点给出判定：
  - valid：逻辑自洽、推理合理
  - flawed：存在逻辑谬误或推理错误（指出具体谬误类型）
  - needs_context：论点本身合理但缺少关键上下文才能成立
  - unverifiable：无法在当前信息下判断对错
- 如果发现某方使用了认知偏误（确认偏误、幸存者偏误等），明确指出
- 给出整体评估（overallAssessment），概括本轮论证质量

## 输出格式
严格输出以下 JSON 格式，不要包含任何其他文字：
{
  "checks": [
    {
      "targetArgumentId": "ADV-R1-01",
      "verdict": "valid",
      "explanation": "该论点逻辑自洽...",
      "correction": "（可选）修正建议"
    }
  ],
  "overallAssessment": "本轮整体论证质量评估..."
}`;
}

export function buildFactCheckerUserMessage(input: AgentInput): string {
  let msg = `## 决策问题\n${input.question}\n`;
  if (input.context) {
    msg += `\n## 补充背景\n${input.context}\n`;
  }
  msg += `\n## 本轮需要校验的论点和反驳\n`;
  msg += formatCurrentRoundArguments(input);
  msg += `\n请对以上所有论点进行事实和逻辑校验。`;
  return msg;
}
