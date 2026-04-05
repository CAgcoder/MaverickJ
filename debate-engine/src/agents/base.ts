import { z } from "zod";
import type { AgentInput } from "../types/index.js";
import { callLLM, type LLMCallResult, type LLMMessage } from "../llm/client.js";
import { parseResponse } from "../llm/responseParser.js";

export interface AgentCallMetrics {
  inputTokens: number;
  outputTokens: number;
}

export abstract class BaseAgent<T> {
  protected abstract readonly role: string;
  protected abstract readonly schema: z.ZodType<T>;

  protected abstract buildSystemPrompt(input: AgentInput): string;
  protected abstract buildUserMessage(input: AgentInput): string;

  async execute(input: AgentInput): Promise<{ result: T; metrics: AgentCallMetrics }> {
    const systemPrompt = this.buildSystemPrompt(input);
    const userMessage = this.buildUserMessage(input);

    const messages: LLMMessage[] = [{ role: "user", content: userMessage }];

    let llmResult: LLMCallResult;
    let lastError: Error | null = null;

    // Try up to 2 times if JSON parsing fails
    for (let attempt = 0; attempt < 2; attempt++) {
      llmResult = await callLLM(
        systemPrompt,
        attempt === 0 ? messages : [
          ...messages,
          { role: "assistant", content: llmResult!.content },
          {
            role: "user",
            content: "你的输出不是合法的 JSON 格式。请严格按照要求的 JSON schema 重新输出，不要包含任何其他文字。",
          },
        ],
        input.config.model,
        input.config.temperature
      );

      try {
        const result = parseResponse(llmResult.content, this.schema);
        return {
          result,
          metrics: {
            inputTokens: llmResult.inputTokens,
            outputTokens: llmResult.outputTokens,
          },
        };
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        console.warn(
          `[${this.role}] JSON 解析失败 (尝试 ${attempt + 1}/2): ${lastError.message}`
        );
      }
    }

    throw new Error(
      `[${this.role}] 无法解析 LLM 输出为合法 JSON: ${lastError?.message}`
    );
  }
}
