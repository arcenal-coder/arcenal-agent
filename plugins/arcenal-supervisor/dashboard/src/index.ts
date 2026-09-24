import { applyGatewayEvent, canSubmitMessage, normalizeHistory, synchronizeChat, type ArcenalChatMessage, type ArcenalChatState, type ChatConnectionState, type GatewayEventLike, type PendingApproval } from "./chat-state";

type UnknownRecord = Record<string, unknown>;
type GatewayClient = {
  close(): void;
  connect(): Promise<void>;
  on(type: string, handler: (event: GatewayEventLike) => void): () => void;
  onState(handler: (state: ChatConnectionState) => void): () => void;
  request<Result>(method: string, params?: UnknownRecord): Promise<Result>;
};
type ReactApi = typeof import("react");

interface SessionSummary { id: string; preview?: string; title?: string }
interface SessionListResponse { sessions?: SessionSummary[] }
interface SessionResponse { inflight?: unknown; messages?: unknown[]; running?: boolean; session_id: string; session_key?: string; stored_session_id?: string }
interface Overview { health?: string; incidents?: unknown[]; platform?: { hostname?: string }; services?: Array<{ healthy?: boolean }> }

const SDK = window.__HERMES_PLUGIN_SDK__!;
const REGISTRY = window.__HERMES_PLUGINS__!;

if (!SDK || !REGISTRY) throw new Error("Le SDK du tableau de bord est indisponible.");

const React = SDK.React as ReactApi;
const h = React.createElement;
const api = <Result>(path: string, options?: RequestInit): Promise<Result> => SDK.fetchJSON(`/api/plugins/arcenal-supervisor${path}`, options);

const INITIAL_CHAT: ArcenalChatState = {
  activity: "", busy: false, error: "", messages: [], pendingApproval: null, sessionId: "", storedSessionId: "", streamingText: "",
};

const SESSION_PARAMS = { close_on_disconnect: true, follow_profile_config: true, source: "desktop" } as const;

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Une erreur inattendue empêche ARC de répondre.";
}

function conversationTitle(session: SessionSummary): string {
  return session.title?.trim() || session.preview?.trim() || "Conversation sans titre";
}

function ConnectionBadge({ state }: { state: ChatConnectionState }): ReturnType<typeof h> {
  const labels: Record<ChatConnectionState, string> = { closed: "Déconnecté", connecting: "Connexion…", error: "Connexion impossible", idle: "En attente", open: "ARC disponible" };
  return h("span", { className: `arc-chat-status is-${state}` }, h("i"), labels[state]);
}

function EmptyConversation({ onPrompt }: { onPrompt: (prompt: string) => void }): ReturnType<typeof h> {
  const prompts = ["Analyse l’état du serveur", "Vérifie les services critiques", "Prépare un rapport de maintenance"];
  return h("section", { className: "arc-chat-empty" },
    h("div", { className: "arc-chat-orb" }, "A"), h("h2", null, "Bonjour, je suis ARC"),
    h("p", null, "Je supervise ARCenal Système et vous accompagne dans son administration."),
    h("div", { className: "arc-chat-suggestions" }, prompts.map((prompt) => h("button", { key: prompt, onClick: () => onPrompt(prompt), type: "button" }, prompt))),
  );
}

function Message({ message }: { message: ArcenalChatMessage }): ReturnType<typeof h> {
  return h("article", { className: `arc-chat-message is-${message.role}` },
    h("span", { className: "arc-chat-avatar" }, message.role === "assistant" ? "ARC" : "Vous"),
    h("div", null, h("p", null, message.text)),
  );
}

function Transcript({ chat, onPrompt }: { chat: ArcenalChatState; onPrompt: (prompt: string) => void }): ReturnType<typeof h> {
  const items = chat.messages.map((message) => h(Message, { key: message.id, message }));
  if (chat.streamingText) items.push(h(Message, { key: "stream", message: { id: "stream", role: "assistant", text: chat.streamingText } }));
  return h("div", { className: "arc-chat-transcript", role: "log", "aria-live": "polite" },
    items.length ? items : h(EmptyConversation, { onPrompt }),
    chat.activity && h("p", { className: "arc-chat-activity" }, h("i"), chat.activity),
  );
}

function ApprovalCard({ approval, onAnswer }: { approval: PendingApproval; onAnswer: (choice: string) => void }): ReturnType<typeof h> {
  const allowed = approval.choices.filter((choice) => choice !== "deny");
  const label = (choice: string): string => choice === "once" ? "Autoriser une fois" : choice === "session" ? "Pour cette session" : "Toujours autoriser";
  return h("section", { className: "arc-chat-approval", role: "alertdialog" },
    h("strong", null, "Autorisation administrateur requise"), h("p", null, approval.description),
    approval.command && h("code", null, approval.command),
    h("div", null, allowed.map((choice) => h("button", { key: choice, onClick: () => onAnswer(choice), type: "button" }, label(choice))), h("button", { className: "is-deny", onClick: () => onAnswer("deny"), type: "button" }, "Refuser")),
  );
}

function Composer({ busy, connection, onSend, onStop }: { busy: boolean; connection: ChatConnectionState; onSend: (text: string) => void; onStop: () => void }): ReturnType<typeof h> {
  const [text, setText] = React.useState("");
  const submit = (): void => { if (!canSubmitMessage(text, connection, busy)) return; onSend(text.trim()); setText(""); };
  const keyDown = (event: KeyboardEvent): void => { if (event.key !== "Enter" || event.shiftKey) return; event.preventDefault(); submit(); };
  const change = (event: Event): void => setText((event.target as HTMLTextAreaElement).value);
  return h("div", { className: "arc-chat-composer" },
    h("textarea", { "aria-label": "Message à ARC", disabled: connection !== "open", onChange: change, onKeyDown: keyDown, placeholder: "Demandez à ARC d’analyser, configurer ou réparer…", rows: 2, value: text }),
    busy ? h("button", { className: "is-stop", onClick: onStop, type: "button" }, "Arrêter") : h("button", { disabled: !canSubmitMessage(text, connection, busy), onClick: submit, type: "button" }, "Envoyer"),
  );
}

function SessionPanel({ active, onNew, onResume, sessions }: { active: string; onNew: () => void; onResume: (id: string) => void; sessions: SessionSummary[] }): ReturnType<typeof h> {
  return h("aside", { className: "arc-chat-sessions" },
    h("button", { className: "arc-chat-new", onClick: onNew, type: "button" }, "+ Nouvelle conversation"), h("h2", null, "Historique"),
    h("nav", null, sessions.map((session) => h("button", { className: session.id === active ? "is-active" : "", key: session.id, onClick: () => onResume(session.id), type: "button" }, conversationTitle(session)))),
  );
}

function SystemSummary({ overview }: { overview: Overview | null }): ReturnType<typeof h> {
  const serviceCount = overview?.services?.filter((service) => service.healthy).length ?? 0;
  const total = overview?.services?.length ?? 0;
  return h("aside", { className: "arc-chat-system" }, h("small", null, "SUPERVISION"),
    h("strong", null, overview?.platform?.hostname || "ARCenal Système"),
    h("span", { className: overview?.health === "healthy" ? "is-healthy" : "is-warning" }, overview?.health === "healthy" ? "Système opérationnel" : "Attention requise"),
    h("dl", null, h("div", null, h("dt", null, "Services"), h("dd", null, `${serviceCount}/${total}`)), h("div", null, h("dt", null, "Incidents"), h("dd", null, String(overview?.incidents?.length ?? 0)))),
    h("small", { className: "arc-chat-engine" }, "Moteur Hermes"));
}

function useGateway(): { chat: ArcenalChatState; connection: ChatConnectionState; client: GatewayClient | null; setChat: React.Dispatch<React.SetStateAction<ArcenalChatState>> } {
  const [chat, setChat] = React.useState<ArcenalChatState>(INITIAL_CHAT);
  const [connection, setConnection] = React.useState<ChatConnectionState>("idle");
  const [client, setClient] = React.useState<GatewayClient | null>(null);
  React.useEffect(() => {
    const gateway = SDK.gateway.createClient() as GatewayClient;
    const offState = gateway.onState(setConnection);
    const eventNames = ["message.start", "message.delta", "message.complete", "status.update", "tool.start", "approval.request", "error"];
    const offEvents = eventNames.map((type) => gateway.on(type, (event) => setChat((current) => applyGatewayEvent(current, event))));
    setClient(gateway);
    void gateway.connect().catch((cause) => setChat((current) => ({ ...current, error: errorMessage(cause) })));
    return () => { offState(); offEvents.forEach((off) => off()); gateway.close(); };
  }, []);
  return { chat, connection, client, setChat };
}

function ArcenalChatPage(): ReturnType<typeof h> {
  const { chat, connection, client, setChat } = useGateway();
  const [sessions, setSessions] = React.useState<SessionSummary[]>([]);
  const [overview, setOverview] = React.useState<Overview | null>(null);
  const refreshSessions = React.useCallback(async (): Promise<void> => {
    if (!client) return;
    const response = await client.request<SessionListResponse>("session.list", { limit: 20 });
    setSessions(response.sessions ?? []);
  }, [client]);
  const createSession = React.useCallback(async (): Promise<void> => {
    if (!client || connection !== "open") return;
    try {
      const response = await client.request<SessionResponse>("session.create", SESSION_PARAMS);
      setChat({ ...INITIAL_CHAT, sessionId: response.session_id, storedSessionId: response.stored_session_id ?? response.session_key ?? response.session_id });
      await refreshSessions();
    } catch (cause) {
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    }
  }, [client, connection, refreshSessions, setChat]);
  React.useEffect(() => { if (connection === "open" && !chat.sessionId) void createSession(); }, [chat.sessionId, connection, createSession]);
  React.useEffect(() => { void api<Overview>("/overview").then(setOverview).catch(() => setOverview(null)); }, []);
  const resume = async (storedId: string): Promise<void> => {
    if (!client) return;
    try {
      const response = await client.request<SessionResponse>("session.resume", { session_id: storedId, source: "desktop" });
      setChat({ ...INITIAL_CHAT, messages: normalizeHistory(response.messages ?? []), sessionId: response.session_id, storedSessionId: response.session_key ?? response.stored_session_id ?? storedId });
    } catch (cause) {
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    }
  };
  const send = async (text: string): Promise<void> => {
    if (!client || !chat.sessionId) return;
    const message: ArcenalChatMessage = { id: `user-${Date.now()}`, role: "user", text };
    setChat((current) => ({ ...current, activity: "ARC analyse votre demande…", busy: true, error: "", messages: [...current.messages, message] }));
    await client.request("prompt.submit", { session_id: chat.sessionId, text }).catch((cause) => setChat((current) => ({ ...current, busy: false, error: errorMessage(cause) })));
  };
  React.useEffect(() => {
    if (!client || !chat.busy || !chat.storedSessionId) return;
    const timer = window.setInterval(() => {
      void client.request<SessionResponse>("session.resume", { session_id: chat.storedSessionId, source: "desktop" })
        .then((snapshot) => setChat((current) => synchronizeChat(current, snapshot)))
        .catch((cause) => setChat((current) => ({ ...current, error: errorMessage(cause) })));
    }, 5000);
    return () => window.clearInterval(timer);
  }, [chat.busy, chat.storedSessionId, client, setChat]);
  const stop = (): void => { if (client && chat.sessionId) void client.request("session.interrupt", { session_id: chat.sessionId }); };
  const answerApproval = async (choice: string): Promise<void> => {
    if (!client || !chat.pendingApproval) return;
    await client.request("approval.respond", { choice, request_id: chat.pendingApproval.requestId, session_id: chat.sessionId });
    setChat((current) => ({ ...current, pendingApproval: null }));
  };
  return h("main", { className: "arc-chat-page" },
    h("header", { className: "arc-chat-heading" }, h("div", null, h("small", null, "ARC · ARCHITECTE D’ARCENAL SYSTÈME"), h("h1", null, "Centre de commande")), h(ConnectionBadge, { state: connection })),
    chat.error && h("p", { className: "arc-chat-error", role: "alert" }, chat.error),
    h("div", { className: "arc-chat-layout" }, h(SessionPanel, { active: chat.sessionId, onNew: () => void createSession(), onResume: (id) => void resume(id), sessions }), h("section", { className: "arc-chat-main" }, h(Transcript, { chat, onPrompt: send }), chat.pendingApproval && h(ApprovalCard, { approval: chat.pendingApproval, onAnswer: (choice) => void answerApproval(choice) }), h(Composer, { busy: chat.busy, connection, onSend: (text) => void send(text), onStop: stop })), h(SystemSummary, { overview })),
  );
}

REGISTRY.register("arcenal-supervisor", ArcenalChatPage);
