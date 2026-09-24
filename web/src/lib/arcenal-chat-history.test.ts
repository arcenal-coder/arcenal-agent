import { describe, expect, it, vi } from "vitest";
import { applyChatHistoryAction } from "./arcenal-chat-history";

describe("historique du chat ARC", () => {
  it("archive une conversation sans la supprimer", async () => {
    const client = { archiveSession: vi.fn().mockResolvedValue({ ok: true }), deleteSession: vi.fn() };
    await applyChatHistoryAction("archive", "session-1", client);
    expect(client.archiveSession).toHaveBeenCalledWith("session-1");
    expect(client.deleteSession).not.toHaveBeenCalled();
  });

  it("supprime définitivement la conversation choisie", async () => {
    const client = { archiveSession: vi.fn(), deleteSession: vi.fn().mockResolvedValue({ ok: true }) };
    await applyChatHistoryAction("delete", "session-2", client);
    expect(client.deleteSession).toHaveBeenCalledWith("session-2");
  });

  it("refuse une conversation sans identifiant", async () => {
    const client = { archiveSession: vi.fn(), deleteSession: vi.fn() };
    await expect(applyChatHistoryAction("archive", " ", client)).rejects.toThrow("introuvable");
  });
});
