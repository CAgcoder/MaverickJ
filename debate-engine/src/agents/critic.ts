import { z } from "zod";
import type { AgentInput, AgentResponse } from "../types/index.js";
import { BaseAgent } from "./base.js";
import { AgentResponseSchema } from "../llm/responseParser.js";
import { buildCriticSystemPrompt, buildCriticUserMessage } from "../prompts/critic.prompt.js";

export class CriticAgent extends BaseAgent<AgentResponse> {
  protected readonly role = "critic";
  protected readonly schema: z.ZodType<AgentResponse> = AgentResponseSchema;

  protected buildSystemPrompt(input: AgentInput): string {
    return buildCriticSystemPrompt(input);
  }

  protected buildUserMessage(input: AgentInput): string {
    return buildCriticUserMessage(input);
  }
}
