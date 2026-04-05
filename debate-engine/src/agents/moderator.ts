import { z } from "zod";
import type { AgentInput, ModeratorResponse } from "../types/index.js";
import { BaseAgent } from "./base.js";
import { ModeratorResponseSchema } from "../llm/responseParser.js";
import { buildModeratorSystemPrompt, buildModeratorUserMessage } from "../prompts/moderator.prompt.js";

export class ModeratorAgent extends BaseAgent<ModeratorResponse> {
  protected readonly role = "moderator";
  protected readonly schema: z.ZodType<ModeratorResponse> = ModeratorResponseSchema;

  protected buildSystemPrompt(input: AgentInput): string {
    return buildModeratorSystemPrompt(input);
  }

  protected buildUserMessage(input: AgentInput): string {
    return buildModeratorUserMessage(input);
  }
}
