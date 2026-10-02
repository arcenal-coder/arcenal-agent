import { describe, expect, it } from "vitest";
import {
  applyGatewayEvent,
  canSubmitMessage,
  chatMessagePresentation,
  completeMaintenance,
  gatewaySessionParams,
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
  pendingMaintenance: null,
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

  it("transforme une proposition de réparation en validation administrateur", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "tool.complete",
      session_id: "session-active",
      payload: {
        name: "arcenal_repair",
        result: {
          status: "control_panel_required",
          proposal: { description: "Recharger Nginx", operation: "nginx.reload", risk: "critical", service: null },
        },
      },
    });

    expect(next.pendingMaintenance).toEqual({ description: "Recharger Nginx", operation: "nginx.reload", risk: "critical", service: null });
  });

  it("ignore un résultat de réparation incomplet", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "tool.complete", session_id: "session-active", payload: { name: "arcenal_repair", result: {} },
    });

    expect(next.pendingMaintenance).toBeNull();
  });

  it("confirme dans le chat une maintenance exécutée", () => {
    const state = { ...INITIAL_STATE, pendingMaintenance: { description: "Recharger", operation: "nginx.reload", risk: "medium", service: null } };

    const next = completeMaintenance(state, "nginx.reload");

    expect(next.pendingMaintenance).toBeNull();
    expect(next.messages.at(-1)?.text).toContain("exécutée et journalisée");
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
    expect(next.activity).toBe("");
    expect(next.streamingText).toBe("");
  });

  it("présente un quota Gemini épuisé sans secret et libère le chat", () => {
    const state = { ...INITIAL_STATE, activity: "ARC analyse votre demande…", streamingText: "Début" };
    const next = applyGatewayEvent(state, {
      type: "error",
      session_id: "session-active",
      payload: { message: "Gemini HTTP 429 RESOURCE_EXHAUSTED api_key=secret-test" },
    });

    expect(next).toMatchObject({ activity: "", busy: false, streamingText: "" });
    expect(next.error).toBe("Le fournisseur Gemini a refusé la requête car le quota disponible est épuisé.");
    expect(next.error).not.toContain("secret-test");
    expect(canSubmitMessage("Nouvelle demande", "open", next.busy)).toBe(true);
  });

  it("présente une saturation Gemini sans bloquer le chat", () => {
    const state = { ...INITIAL_STATE, activity: "ARC analyse votre demande…", streamingText: "Début" };
    const next = applyGatewayEvent(state, {
      type: "error",
      session_id: "session-active",
      payload: { message: "Gemini HTTP 503 (UNAVAILABLE): high demand api_key=secret-test" },
    });

    expect(next).toMatchObject({ activity: "", busy: false, streamingText: "" });
    expect(next.error).toContain("temporairement saturé");
    expect(next.error).not.toContain("secret-test");
    expect(canSubmitMessage("Nouvelle demande", "open", next.busy)).toBe(true);
  });

  it("expurge les identifiants d’une erreur fournisseur générique", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "error",
      session_id: "session-active",
      payload: { message: "Upstream HTTP 503: {\"api_key\":\"secret-test\"} Bearer abc.def" },
    });

    expect(next.error).toContain("api_key=[masqué]");
    expect(next.error).toContain("Bearer [masqué]");
    expect(next.error).not.toContain("secret-test");
    expect(next.error).not.toContain("abc.def");
  });

  it("libère aussi le chat après un message final en erreur 503", () => {
    const next = applyGatewayEvent(INITIAL_STATE, {
      type: "message.complete",
      session_id: "session-active",
      payload: { status: "error", error: "Gemini HTTP 503 UNAVAILABLE", text: "échec" },
    });

    expect(next).toMatchObject({ activity: "", busy: false, streamingText: "" });
    expect(next.error).toContain("temporairement saturé");
  });

  it("relie la bulle utilisateur aux tokens de contraste du thème", () => {
    expect(chatMessagePresentation("user")).toMatchObject({
      "--color-foreground": "var(--arc-primary-text)",
      "--color-primary": "var(--arc-primary-text)",
      backgroundColor: "var(--arc-primary)",
      color: "var(--arc-primary-text)",
    });
    expect(chatMessagePresentation("assistant")).toBeUndefined();
  });

  it("crée le chat avec le modèle de l’agent ARC sans suivre Hermes", () => {
    const params = gatewaySessionParams({ agent_id: "arc", mode: "auto", model: "openai/gpt-4.1-mini", provider: "openrouter", registry_id: "openrouter-model" });

    expect(params).toMatchObject({ follow_profile_config: false, model: "openai/gpt-4.1-mini", provider: "openrouter" });
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
