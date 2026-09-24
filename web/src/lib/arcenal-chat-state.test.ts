import { describe, expect, it } from "vitest";
import {
  applyGatewayEvent,
  canSubmitMessage,
  normalizeHistory,
  type ArcenalChatState,
} from "../../../plugins/arcenal-supervisor/dashboard/src/chat-state";

const INITIAL_STATE: ArcenalChatState = {
  activity: "",
  busy: true,
  error: "",
  messages: [],
  pendingApproval: null,
  sessionId: "session-active",
  streamingText: "",
};

describe("état du chat ARC", () => {
  it("assemble le flux puis publie la réponse finale", () => {
    const streamed = applyGatewayEvent(INITIAL_STATE, {
      type: "message.delta", session_id: "session-active", payload: { text: "Bon" },
    });
    const completed = applyGatewayEvent(streamed, {
      type: "message.complete", session_id: "session-active", payload: { text: "Bonjour" },
    });

    expect(streamed.streamingText).toBe("Bon");
    expect(completed.messages.at(-1)).toMatchObject({ role: "assistant", text: "Bonjour" });
    expect(completed.busy).toBe(false);
  });

  it("ignore les événements appartenant à une autre conversation", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "message.delta", session_id: "session-other", payload: { text: "Secret" },
    });

    expect(next).toBe(INITIAL_STATE);
  });

  it("normalise l’historique sans afficher les traces techniques", () => {
    const messages = normalizeHistory([
      { role: "user", text: "État du serveur ?" },
      { role: "tool", text: "systemctl" },
      { role: "assistant", text: "Tous les services sont actifs." },
    ]);

    expect(messages).toEqual([
      { id: "history-0", role: "user", text: "État du serveur ?" },
      { id: "history-2", role: "assistant", text: "Tous les services sont actifs." },
    ]);
  });

  it("interdit les envois vides, hors connexion ou pendant une réponse", () => {
    expect(canSubmitMessage("bonjour", "open", false)).toBe(true);
    expect(canSubmitMessage("   ", "open", false)).toBe(false);
    expect(canSubmitMessage("bonjour", "closed", false)).toBe(false);
    expect(canSubmitMessage("bonjour", "open", true)).toBe(false);
  });

  it("présente une demande d’autorisation explicite", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "approval.request",
      session_id: "session-active",
      payload: { request_id: "approval-1", description: "Redémarrer Nginx", choices: ["once", "deny"] },
    });

    expect(next.pendingApproval).toMatchObject({ requestId: "approval-1", description: "Redémarrer Nginx" });
  });
});
