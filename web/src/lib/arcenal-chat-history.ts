export type ChatHistoryAction = "archive" | "delete";

export class ChatHistoryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ChatHistoryError";
  }
}

interface ChatHistoryApi {
  archiveSession: (id: string) => Promise<{ ok: boolean }>;
  deleteSession: (id: string) => Promise<{ ok: boolean }>;
}

export async function applyChatHistoryAction(action: ChatHistoryAction, sessionId: string, client: ChatHistoryApi): Promise<void> {
  const id = sessionId.trim();
  if (!id) throw new ChatHistoryError("La conversation est introuvable.");
  if (action === "archive") await client.archiveSession(id);
  else await client.deleteSession(id);
}
