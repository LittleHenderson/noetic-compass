import { getApiBase } from "./apiCore";

export interface AssistantTurn {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantReply {
  reply: string;
  source: string;
  model?: string;
  needs?: string;
}

export async function postAssistantChat(
  message: string,
  history: AssistantTurn[],
): Promise<AssistantReply> {
  const res = await fetch(`${getApiBase()}/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return (await res.json()) as AssistantReply;
}
