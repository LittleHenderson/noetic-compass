import { apiPostJson } from "./apiCore";
import type { CommandPreview, ProposedCommand } from "./ownerCommandApi";

export interface AssistantTurn {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantReply {
  reply: string;
  source: string;
  model?: string;
  needs?: string;
  proposed_command?: ProposedCommand | null;
  command_preview?: CommandPreview | null;
}

export async function postAssistantChat(
  message: string,
  history: AssistantTurn[],
): Promise<AssistantReply> {
  return apiPostJson<AssistantReply, { message: string; history: AssistantTurn[] }>(
    "/assistant/chat",
    { message, history },
    60_000,
  );
}
