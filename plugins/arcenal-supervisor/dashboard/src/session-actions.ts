type JsonFetcher = <Result>(url: string, init?: RequestInit) => Promise<Result>;

export class SessionArchiveError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SessionArchiveError";
  }
}

export async function archiveConversation(fetcher: JsonFetcher, sessionId: string): Promise<void> {
  const id = sessionId.trim();
  if (!id) throw new SessionArchiveError("La conversation active est introuvable.");
  try {
    await fetcher(`/api/sessions/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ archived: true }),
    });
  } catch (cause) {
    throw new SessionArchiveError(
      cause instanceof Error ? `L’archivage a échoué : ${cause.message}` : "L’archivage de la conversation a échoué.",
    );
  }
}
