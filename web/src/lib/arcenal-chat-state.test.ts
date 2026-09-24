import { describe, expect, it } from "vitest";
import {
  applyGatewayEvent,
  canSubmitMessage,
  normalizeHistory,
  synchronizeChat,
  type ArcenalChatState,
} from "../../../plugins/arcenal-supervisor/dashboard/src/chat-state";

const INITIAL_STATE: ArcenalChatState = {
  activity: "",
  busy: true,
  error: "",
  messages: [],
  pendingApproval: null,
  sessionId: "session-active",
  storedSessionId: "stored-active",
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

  it("récupère une réponse terminée si le flux temps réel a été manqué", () => {
    const next = synchronizeChat(INITIAL_STATE, {
      messages: [
        { role: "user", text: "État du serveur ?" },
        { role: "assistant", text: "Le serveur est opérationnel." },
      ],
      running: false,
    });

    expect(next.busy).toBe(false);
    expect(next.messages.at(-1)?.text).toBe("Le serveur est opérationnel.");
  });

  it("affiche la réponse partielle pendant une resynchronisation", () => {
    const next = synchronizeChat(INITIAL_STATE, {
      inflight: { assistant: "Je vérifie les services", streaming: true },
      running: true,
    });

    expect(next.busy).toBe(true);
    expect(next.streamingText).toBe("Je vérifie les services");
    expect(next.activity).toBe("ARC analyse votre demande…");
  });

  it("remonte clairement une erreur de fournisseur", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "message.complete",
      session_id: "session-active",
      payload: { status: "error", error: "Clé API OpenRouter refusée", text: "Error" },
    });

    expect(next.busy).toBe(false);
    expect(next.error).toBe("Clé API OpenRouter refusée");
  });

  it("ignore une resynchronisation tardive après la réponse finale", () => {
    const settled = { ...INITIAL_STATE, busy: false, messages: [{ id: "final", role: "assistant" as const, text: "Terminé" }] };
    const next = synchronizeChat(settled, {
      inflight: { assistant: "Ancienne réponse partielle", streaming: true },
      running: true,
    });

    expect(next).toBe(settled);
  });
});
