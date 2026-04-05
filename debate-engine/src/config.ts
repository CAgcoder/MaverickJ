import dotenv from "dotenv";
import type { DebateConfig } from "./types/index.js";

dotenv.config();

export function getApiKey(): string {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key || key === "sk-ant-xxxxx") {
    throw new Error("请在 .env 文件中设置 ANTHROPIC_API_KEY");
  }
  return key;
}

export function getDefaultConfig(): DebateConfig {
  return {
    maxRounds: parseInt(process.env.MAX_ROUNDS || "5", 10),
    convergenceThreshold: parseInt(process.env.CONVERGENCE_THRESHOLD || "2", 10),
    model: process.env.MODEL_NAME || "claude-sonnet-4-20250514",
    temperature: parseFloat(process.env.TEMPERATURE || "0.7"),
    language: (process.env.LANGUAGE as "zh" | "en") || "zh",
  };
}
