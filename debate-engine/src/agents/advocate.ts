import { z } from "zod";
import type { AgentInput, AgentResponse } from "../types/index.js";
import { BaseAgent } from "./base.js";
import { AgentResponseSchema } from "../llm/responseParser.js";
import { buildAdvocateSystemPrompt, buildAdvocateUserMessage } from "../prompts/advocate.prompt.js";

export class AdvocateAgent extends BaseAgent<AgentResponse> {
  protected readonly role = "advocate";
  protected readonly schema: z.ZodType<AgentResponse> = AgentResponseSchema;

  protected buildSystemPrompt(input: AgentInput): string {
    return buildAdvocateSystemPrompt(input);
  }

  protected buildUserMessage(input: AgentInput): string {
    return buildAdvocateUserMessage(input);
  }
}
