import Anthropic from "@anthropic-ai/sdk";
import { getApiKey } from "../config.js";

export interface LLMCallResult {
  content: string;
  inputTokens: number;
  outputTokens: number;
}

export interface LLMMessage {
  role: "user" | "assistant";
  content: string;
}

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

let clientInstance: Anthropic | null = null;

function getClient(): Anthropic {
  if (!clientInstance) {
    clientInstance = new Anthropic({ apiKey: getApiKey() });
  }
  return clientInstance;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function callLLM(
  systemPrompt: string,
  messages: LLMMessage[],
  model: string,
  temperature: number,
  maxTokens: number = 4096
): Promise<LLMCallResult> {
  const client = getClient();

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await client.messages.create({
        model,
        max_tokens: maxTokens,
        temperature,
        system: systemPrompt,
        messages: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });

      const textBlock = response.content.find((b) => b.type === "text");
      const content = textBlock ? textBlock.text : "";

      return {
        content,
        inputTokens: response.usage.input_tokens,
        outputTokens: response.usage.output_tokens,
      };
    } catch (error: unknown) {
      if (attempt < MAX_RETRIES) {
        const msg = error instanceof Error ? error.message : String(error);
        console.warn(`LLM 调用失败 (尝试 ${attempt + 1}/${MAX_RETRIES + 1}): ${msg}`);
        await sleep(RETRY_DELAY_MS * (attempt + 1));
        continue;
      }
      throw error;
    }
  }

  throw new Error("LLM 调用失败：超过最大重试次数");
}
