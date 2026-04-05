import { runDebate, type DebateCallbacks } from "./orchestrator/engine.js";
import { getDefaultConfig } from "./config.js";
import { renderReportToMarkdown } from "./output/reportRenderer.js";
import {
  printRoundStart,
  printAgentStart,
  printAdvocateResult,
  printCriticResult,
  printFactCheckResult,
  printModeratorResult,
  printDebateComplete,
} from "./output/streamHandler.js";
import type { AgentResponse, FactCheckResponse, ModeratorResponse } from "./types/index.js";
import * as fs from "fs";
import * as readline from "readline";

async function askQuestion(prompt: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(prompt, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function main(): Promise<void> {
  console.log("");
  console.log("╔══════════════════════════════════════════════════════════╗");
  console.log("║          🏛️  多 Agent 辩论式决策引擎                      ║");
  console.log("║          Multi-Agent Debate Decision Engine             ║");
  console.log("╚══════════════════════════════════════════════════════════╝");
  console.log("");

  // Get question from CLI args or interactive input
  let question = process.argv[2];
  let context: string | undefined;

  if (!question) {
    question = await askQuestion("🎯 请输入你的决策问题: ");
    if (!question) {
      console.error("错误：请提供决策问题");
      process.exit(1);
    }
    const contextInput = await askQuestion("📋 补充背景（可选，直接回车跳过）: ");
    if (contextInput) {
      context = contextInput;
    }
  } else {
    context = process.argv[3];
  }

  const config = getDefaultConfig();

  console.log("");
  console.log(`📌 决策问题: ${question}`);
  if (context) console.log(`📋 补充背景: ${context}`);
  console.log(`⚙️  配置: 最大 ${config.maxRounds} 轮 | 模型 ${config.model} | 温度 ${config.temperature}`);
  console.log("");

  const callbacks: DebateCallbacks = {
    onRoundStart: (round) => printRoundStart(round),
    onAgentStart: (agent) => printAgentStart(agent),
    onAgentComplete: (agent, _round, result) => {
      switch (agent) {
        case "advocate":
          printAdvocateResult(result as AgentResponse);
          break;
        case "critic":
          printCriticResult(result as AgentResponse);
          break;
        case "fact-checker":
          printFactCheckResult(result as FactCheckResponse);
          break;
        case "moderator":
          printModeratorResult(result as ModeratorResponse);
          break;
      }
    },
    onDebateEnd: (state) => {
      printDebateComplete(state.status, state.convergenceReason);
    },
  };

  try {
    const state = await runDebate(question, config, context, callbacks);

    if (state.finalReport) {
      const markdown = renderReportToMarkdown(state.finalReport, state);

      // Print report to console
      console.log(markdown);

      // Save to file
      const filename = `debate-report-${state.id.slice(0, 8)}.md`;
      fs.writeFileSync(filename, markdown, "utf-8");
      console.log(`\n📄 报告已保存至: ${filename}`);

      // Also save full state as JSON for debugging
      const jsonFilename = `debate-state-${state.id.slice(0, 8)}.json`;
      fs.writeFileSync(jsonFilename, JSON.stringify(state, null, 2), "utf-8");
      console.log(`📦 完整辩论数据已保存至: ${jsonFilename}`);
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`\n❌ 辩论执行失败: ${msg}`);
    process.exit(1);
  }
}

main();
