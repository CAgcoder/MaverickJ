import { runDebate, type DebateCallbacks } from "../orchestrator/engine.js";
import { getDefaultConfig } from "../config.js";
import { renderReportToMarkdown } from "../output/reportRenderer.js";
import {
  printRoundStart,
  printAgentStart,
  printAdvocateResult,
  printCriticResult,
  printFactCheckResult,
  printModeratorResult,
  printDebateComplete,
} from "../output/streamHandler.js";
import type { AgentResponse, FactCheckResponse, ModeratorResponse } from "../types/index.js";
import * as fs from "fs";

const question = "我们应该自建内部数据分析平台，还是采购现有的商业分析工具（如 Tableau / Power BI）？";
const context = `
我们是一家 200 人的 SaaS 公司，数据团队 15 人（5 数据工程师 + 10 数据分析师）。
当前状况：
1. 使用混合方案：部分用 Metabase（开源），部分用 Excel
2. 数据量：日均处理约 5TB 数据
3. 主要需求：实时仪表盘、自助查询、定期报告
4. 预算约束：年度 IT 预算 300 万，可分配给此项目约 80 万
5. 时间约束：希望 6 个月内有可用方案
6. 数据安全要求高（金融行业）
`;

async function main() {
  const config = getDefaultConfig();

  const callbacks: DebateCallbacks = {
    onRoundStart: (round) => printRoundStart(round),
    onAgentStart: (agent) => printAgentStart(agent),
    onAgentComplete: (agent, _round, result) => {
      switch (agent) {
        case "advocate": printAdvocateResult(result as AgentResponse); break;
        case "critic": printCriticResult(result as AgentResponse); break;
        case "fact-checker": printFactCheckResult(result as FactCheckResponse); break;
        case "moderator": printModeratorResult(result as ModeratorResponse); break;
      }
    },
    onDebateEnd: (state) => printDebateComplete(state.status, state.convergenceReason),
  };

  const state = await runDebate(question, config, context, callbacks);

  if (state.finalReport) {
    const markdown = renderReportToMarkdown(state.finalReport, state);
    fs.writeFileSync("example-build-vs-buy.md", markdown, "utf-8");
    console.log("\n📄 报告已保存至: example-build-vs-buy.md");
  }
}

main().catch(console.error);
