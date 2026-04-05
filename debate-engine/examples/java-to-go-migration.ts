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

const question = "我们团队应该将现有的 Java 后端服务迁移到 Go 语言吗？";
const context = `
我们是一个 50 人的后端团队，主要使用 Java + Spring Boot 技术栈，服务已运行 3 年。
当前面临的问题：
1. 部署成本高（JVM 内存占用大）
2. 冷启动慢，影响 Serverless 场景
3. 部分团队成员对 Go 有兴趣
4. 服务主要是 API Gateway 和微服务
5. 年营收约 5000 万，技术投入预算约 800 万
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
    fs.writeFileSync("example-java-to-go.md", markdown, "utf-8");
    console.log("\n📄 报告已保存至: example-java-to-go.md");
  }
}

main().catch(console.error);
