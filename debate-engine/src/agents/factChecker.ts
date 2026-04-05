import { z } from "zod";
import type { AgentInput, FactCheckResponse } from "../types/index.js";
import { BaseAgent } from "./base.js";
import { FactCheckResponseSchema } from "../llm/responseParser.js";
import { buildFactCheckerSystemPrompt, buildFactCheckerUserMessage } from "../prompts/factChecker.prompt.js";

export class FactCheckerAgent extends BaseAgent<FactCheckResponse> {
  protected readonly role = "fact-checker";
  protected readonly schema: z.ZodType<FactCheckResponse> = FactCheckResponseSchema;

  protected buildSystemPrompt(input: AgentInput): string {
    return buildFactCheckerSystemPrompt(input);
  }

  protected buildUserMessage(input: AgentInput): string {
    return buildFactCheckerUserMessage(input);
  }
}
