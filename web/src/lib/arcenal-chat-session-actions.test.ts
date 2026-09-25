import { describe, expect, it, vi } from "vitest";
import { archiveConversation, SessionArchiveError } from "../../../plugins/arcenal-supervisor/dashboard/src/session-actions";

describe("archivage du chat ARC", () => {
  it("archive la conversation active", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    await archiveConversation(fetcher, "conversation-1");
    expect(fetcher).toHaveBeenCalledWith("/api/sessions/conversation-1", expect.objectContaining({ method: "PATCH" }));
  });

  it("encode les identifiants spéciaux", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    await archiveConversation(fetcher, "conversation/été");
    expect(fetcher).toHaveBeenCalledWith("/api/sessions/conversation%2F%C3%A9t%C3%A9", expect.any(Object));
  });

  it("refuse un identifiant vide", async () => {
    await expect(archiveConversation(vi.fn(), "   ")).rejects.toBeInstanceOf(SessionArchiveError);
  });

  it("restitue un échec d’archivage compréhensible", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("service indisponible"));
    await expect(archiveConversation(fetcher, "conversation-1"))
      .rejects.toThrow("L’archivage a échoué : service indisponible");
  });
});
