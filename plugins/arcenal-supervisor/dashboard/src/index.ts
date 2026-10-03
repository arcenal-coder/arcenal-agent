import { canSubmitMessage, chatMessagePresentation, completeMaintenance, providerErrorMessage, type ArcenalChatMessage, type ArcenalChatState, type ChatConnectionState, type PendingApproval, type PendingMaintenance } from "./chat-state";
import { resumeConversation } from "./session-actions";

type ReactApi = typeof import("react");

interface SessionSummary { id: string; title: string }
interface ChatSession extends SessionSummary { messages: ArcenalChatMessage[] }
interface ChatQueryResponse { session: ChatSession }
interface Overview { health?: string; incidents?: unknown[]; platform?: { hostname?: string }; services?: Array<{ healthy?: boolean }> }
interface ControlAction { consequence: string; description: string; rollback: string }
interface PrepareResponse { action: ControlAction; approval_id?: string; status: "confirmation_required" | "ready" }

const SDK = window.__HERMES_PLUGIN_SDK__!;
const REGISTRY = window.__HERMES_PLUGINS__!;

if (!SDK || !REGISTRY) throw new Error("Le SDK du tableau de bord est indisponible.");

const React = SDK.React as ReactApi;
const h = React.createElement;
const api = <Result>(path: string, options?: RequestInit): Promise<Result> => SDK.fetchJSON(`/api/plugins/arcenal-supervisor${path}`, options);
const controlApi = <Result>(path: string, options?: RequestInit): Promise<Result> => SDK.fetchJSON(`/api/arcenal-control${path}`, options);

const INITIAL_CHAT: ArcenalChatState = {
  activity: "", busy: false, error: "", messages: [], pendingApproval: null, pendingMaintenance: null, sessionId: "", storedSessionId: "", streamingText: "",
};

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Une erreur inattendue empêche ARC de répondre.";
}

function conversationTitle(session: SessionSummary): string {
  return session.title.trim() || "Conversation sans titre";
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
    h("div", { style: chatMessagePresentation(message.role) }, h(SDK.components.Markdown, { content: message.text })),
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

function MaintenanceCard({ busy, maintenance, onExecute }: { busy: boolean; maintenance: PendingMaintenance; onExecute: () => void }): ReturnType<typeof h> {
  return h("section", { className: "arc-chat-maintenance", role: "alertdialog" },
    h("div", null, h("strong", null, "Action proposée par ARC"), h("span", null, `Risque ${maintenance.risk}`)),
    h("p", null, maintenance.description),
    maintenance.service && h("p", null, `Service concerné : ${maintenance.service}`),
    h("button", { disabled: busy, onClick: onExecute, type: "button" }, busy ? "Validation…" : "Vérifier et exécuter"),
  );
}

function requestOptions(body: object): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function confirmAction(action: ControlAction): boolean {
  const message = `${action.description}\n\nConséquence : ${action.consequence}\nRetour arrière : ${action.rollback}`;
  return window.confirm(`${message}\n\nConfirmer cette action administrative ?`);
}

async function executeMaintenance(maintenance: PendingMaintenance): Promise<boolean> {
  const body = { action_id: maintenance.operation, target: maintenance.service };
  const proposal = await controlApi<PrepareResponse>("/actions/prepare", requestOptions(body));
  if (proposal.status === "confirmation_required" && !confirmAction(proposal.action)) return false;
  const prepared = proposal.status === "ready" ? proposal : await controlApi<PrepareResponse>("/actions/prepare", requestOptions({ ...body, human_confirmed: true }));
  await controlApi("/actions/execute", requestOptions({ ...body, approval_id: prepared.approval_id }));
  return true;
}

function Composer({ busy, connection, onSend }: { busy: boolean; connection: ChatConnectionState; onSend: (text: string) => void }): ReturnType<typeof h> {
  const [text, setText] = React.useState("");
  const submit = (): void => { if (!canSubmitMessage(text, connection, busy)) return; onSend(text.trim()); setText(""); };
  const keyDown = (event: KeyboardEvent): void => { if (event.key !== "Enter" || event.shiftKey) return; event.preventDefault(); submit(); };
  const change = (event: Event): void => setText((event.target as HTMLTextAreaElement).value);
  return h("div", { className: "arc-chat-composer" },
    h("textarea", { "aria-label": "Message à ARC", disabled: connection !== "open", onChange: change, onKeyDown: keyDown, placeholder: "Demandez à ARC d’analyser, configurer ou réparer…", rows: 2, value: text }),
    busy ? h("button", { className: "is-stop", disabled: true, type: "button" }, "ARC travaille…") : h("button", { disabled: !canSubmitMessage(text, connection, busy), onClick: submit, type: "button" }, "Envoyer"),
  );
}

function SessionPanel({ active, canArchive, onArchive, onNew, onResume, sessions }: { active: string; canArchive: boolean; onArchive: () => void; onNew: () => void; onResume: (id: string) => void; sessions: SessionSummary[] }): ReturnType<typeof h> {
  return h("aside", { className: "arc-chat-sessions" },
    h("button", { className: "arc-chat-new", onClick: onNew, type: "button" }, "+ Nouvelle conversation"), h("h2", null, "Historique"),
    h("nav", null, sessions.map((session) => h("button", { className: session.id === active ? "is-active" : "", key: session.id, onClick: () => onResume(session.id), type: "button" }, conversationTitle(session)))),
    h("button", { className: "arc-chat-archive", disabled: !canArchive, onClick: onArchive, type: "button" }, "Archiver cette conversation"),
  );
}

function SystemSummary({ overview }: { overview: Overview | null }): ReturnType<typeof h> {
  const serviceCount = overview?.services?.filter((service) => service.healthy).length ?? 0;
  const total = overview?.services?.length ?? 0;
  return h("aside", { className: "arc-chat-system" }, h("small", null, "SUPERVISION"),
    h("strong", null, overview?.platform?.hostname || "ARCenal Système"),
    h("span", { className: overview?.health === "healthy" ? "is-healthy" : "is-warning" }, overview?.health === "healthy" ? "Système opérationnel" : "Attention requise"),
    h("dl", null, h("div", null, h("dt", null, "Services"), h("dd", null, `${serviceCount}/${total}`)), h("div", null, h("dt", null, "Incidents"), h("dd", null, String(overview?.incidents?.length ?? 0)))));
}

function sessionChat(session: ChatSession): ArcenalChatState {
  return { ...INITIAL_CHAT, messages: session.messages, sessionId: session.id, storedSessionId: session.id };
}

function ArcenalChatPage(): ReturnType<typeof h> {
  const [chat, setChat] = React.useState<ArcenalChatState>(INITIAL_CHAT);
  const [connection, setConnection] = React.useState<ChatConnectionState>("connecting");
  const [sessions, setSessions] = React.useState<SessionSummary[]>([]);
  const [overview, setOverview] = React.useState<Overview | null>(null);
  const [maintenanceBusy, setMaintenanceBusy] = React.useState(false);
  const refreshSessions = React.useCallback(async (): Promise<SessionSummary[]> => {
    const available = await api<SessionSummary[]>("/chat/sessions");
    setSessions(available);
    return available;
  }, []);
  const createSession = React.useCallback(async (): Promise<void> => {
    try {
      const session = await api<ChatSession>("/chat/sessions", { method: "POST" });
      setChat(sessionChat(session));
      setConnection("open");
      await refreshSessions();
    } catch (cause) {
      setConnection("error");
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    }
  }, [refreshSessions]);
  const initializeChat = React.useCallback(async (): Promise<void> => {
    try {
      const available = await refreshSessions();
      if (!available[0]) return await createSession();
      const session = await api<ChatSession>(`/chat/sessions/${encodeURIComponent(available[0].id)}`);
      setChat(sessionChat(session));
      setConnection("open");
    } catch (cause) {
      setConnection("error");
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    }
  }, [createSession, refreshSessions]);
  React.useEffect(() => { void initializeChat(); }, [initializeChat]);
  React.useEffect(() => { void api<Overview>("/overview").then(setOverview).catch(() => setOverview(null)); }, []);
  const resume = async (storedId: string): Promise<void> => {
    try {
      const session = await resumeConversation<ChatSession>(api, storedId);
      setChat(sessionChat(session));
      setConnection("open");
    } catch (cause) {
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    }
  };
  const send = async (text: string): Promise<void> => {
    if (!chat.sessionId) return;
    const message: ArcenalChatMessage = { id: `user-${Date.now()}`, role: "user", text };
    setChat((current) => ({ ...current, activity: "ARC analyse votre demande…", busy: true, error: "", messages: [...current.messages, message] }));
    try {
      const response = await api<ChatQueryResponse>(`/chat/sessions/${encodeURIComponent(chat.sessionId)}/messages`, requestOptions({ text }));
      setChat(sessionChat(response.session));
      await refreshSessions();
    } catch (cause) {
      setChat((current) => ({ ...current, activity: "", busy: false, error: providerErrorMessage(errorMessage(cause)), streamingText: "" }));
    }
  };
  const answerApproval = async (_choice: string): Promise<void> => {
    if (!chat.pendingApproval) return;
    setChat((current) => ({ ...current, pendingApproval: null }));
  };
  const archiveActive = async (): Promise<void> => {
    if (!chat.storedSessionId || chat.busy) return;
    if (!window.confirm("Archiver cette conversation et en démarrer une nouvelle ?")) return;
    try {
      await api(`/chat/sessions/${encodeURIComponent(chat.storedSessionId)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ archived: true }) });
      await createSession();
    } catch (cause) {
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    }
  };
  const runMaintenance = async (): Promise<void> => {
    if (!chat.pendingMaintenance || maintenanceBusy) return;
    setMaintenanceBusy(true);
    try {
      const maintenance = chat.pendingMaintenance;
      const completed = await executeMaintenance(maintenance);
      if (completed) setChat((current) => completeMaintenance(current, maintenance.operation));
    } catch (cause) {
      setChat((current) => ({ ...current, error: errorMessage(cause) }));
    } finally {
      setMaintenanceBusy(false);
    }
  };
  return h("main", { className: "arc-chat-page" },
    h("header", { className: "arc-chat-heading" }, h("div", null, h("small", null, "ARC · ARCHITECTE D’ARCENAL SYSTÈME"), h("h1", null, "Centre de commande")), h(ConnectionBadge, { state: connection })),
    chat.error && h("p", { className: "arc-chat-error", role: "alert" }, chat.error),
    h("div", { className: "arc-chat-layout" }, h(SessionPanel, { active: chat.storedSessionId, canArchive: Boolean(chat.storedSessionId) && !chat.busy, onArchive: () => void archiveActive(), onNew: () => void createSession(), onResume: (id) => void resume(id), sessions }), h("section", { className: "arc-chat-main" }, h(Transcript, { chat, onPrompt: send }), chat.pendingMaintenance && h(MaintenanceCard, { busy: maintenanceBusy, maintenance: chat.pendingMaintenance, onExecute: () => void runMaintenance() }), chat.pendingApproval && h(ApprovalCard, { approval: chat.pendingApproval, onAnswer: (choice) => void answerApproval(choice) }), h(Composer, { busy: chat.busy, connection, onSend: (text) => void send(text) })), h(SystemSummary, { overview })),
  );
}

REGISTRY.register("arcenal-supervisor", ArcenalChatPage);
