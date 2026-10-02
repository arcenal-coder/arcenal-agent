export type ChatConnectionState = "idle" | "connecting" | "open" | "closed" | "error";
export type ChatRole = "assistant" | "user";

export interface ArcenalChatMessage {
  id: string;
  role: ChatRole;
  text: string;
}

export interface PendingApproval {
  choices: string[];
  command: string;
  description: string;
  requestId: string;
}

export interface PendingMaintenance {
  description: string;
  operation: string;
  risk: string;
  service: string | null;
}

export interface ArcenalChatState {
  activity: string;
  busy: boolean;
  error: string;
  messages: ArcenalChatMessage[];
  pendingApproval: PendingApproval | null;
  pendingMaintenance: PendingMaintenance | null;
  sessionId: string;
  storedSessionId: string;
  streamingText: string;
}

export interface GatewayEventLike {
  payload?: unknown;
  session_id?: string;
  type: string;
}

export interface AgentRuntimeSelection {
  agent_id: string;
  mode: "auto" | "fixed";
  model: string;
  provider: string;
  registry_id: string;
}

export interface GatewaySessionParams {
  [key: string]: boolean | string;
  close_on_disconnect: boolean;
  follow_profile_config: boolean;
  model: string;
  provider: string;
  source: string;
}

type UnknownRecord = Record<string, unknown>;
export type ChatMessagePresentation = Readonly<Record<string, string>>;

const USER_MESSAGE_PRESENTATION: ChatMessagePresentation = {
  "--color-foreground": "var(--arc-primary-text)",
  "--color-primary": "var(--arc-primary-text)",
  "--midground": "var(--arc-primary-text)",
  backgroundColor: "var(--arc-primary)",
  color: "var(--arc-primary-text)",
};

function record(value: unknown): UnknownRecord {
  return typeof value === "object" && value !== null ? value as UnknownRecord : {};
}

function textField(value: unknown, key: string): string {
  const candidate = record(value)[key];
  return typeof candidate === "string" ? candidate : "";
}

function choicesField(value: unknown): string[] {
  const candidate = record(value).choices;
  return Array.isArray(candidate) ? candidate.filter((item): item is string => typeof item === "string") : [];
}

function assistantMessage(text: string): ArcenalChatMessage {
  return { id: `assistant-${Date.now()}`, role: "assistant", text };
}

export function providerErrorMessage(raw: string): string {
  const normalized = raw.toLocaleLowerCase();
  const quota = normalized.includes("429") || normalized.includes("resource_exhausted");
  if (normalized.includes("gemini") && quota) {
    return "Le fournisseur Gemini a refusé la requête car le quota disponible est épuisé.";
  }
  const unavailable = normalized.includes("503") || normalized.includes("unavailable") || normalized.includes("high demand");
  if (normalized.includes("gemini") && unavailable) {
    return "Le modèle Gemini sollicité est temporairement saturé. Vérifiez le modèle attribué à l’agent ARC ou réessayez dans quelques instants.";
  }
  return redactCredentials(raw) || "La réponse d’ARC a échoué.";
}

function redactCredentials(raw: string): string {
  return raw
    .replace(/\bBearer\s+\S+/gi, "Bearer [masqué]")
    .replace(/\b(api[_ -]?key|token|secret|password|credential|key)["']?\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,}]+)/gi, "$1=[masqué]");
}

export function chatMessagePresentation(role: ChatRole): ChatMessagePresentation | undefined {
  return role === "user" ? USER_MESSAGE_PRESENTATION : undefined;
}

export function gatewaySessionParams(runtime: AgentRuntimeSelection): GatewaySessionParams {
  return {
    close_on_disconnect: true,
    follow_profile_config: false,
    model: runtime.model,
    provider: runtime.provider,
    source: "desktop",
  };
}

function completeMessage(state: ArcenalChatState, payload: unknown): ArcenalChatState {
  const data = record(payload);
  const text = textField(data, "text") || state.streamingText;
  const failed = data.status === "error";
  const messages = text && !failed ? [...state.messages, assistantMessage(text)] : state.messages;
  const rawError = failed ? textField(data, "error") || text : "";
  const error = rawError ? providerErrorMessage(rawError) : "";
  return { ...state, activity: "", busy: false, error, messages, streamingText: "" };
}

function approval(payload: unknown): PendingApproval {
  return {
    choices: choicesField(payload),
    command: textField(payload, "command"),
    description: textField(payload, "description") || "ARC demande votre autorisation.",
    requestId: textField(payload, "request_id"),
  };
}

function maintenance(payload: unknown): PendingMaintenance | null {
  const data = record(payload);
  if (textField(data, "name") !== "arcenal_repair") return null;
  const result = record(data.result);
  if (textField(result, "status") !== "control_panel_required") return null;
  const proposal = record(result.proposal);
  const operation = textField(proposal, "operation");
  const description = textField(proposal, "description");
  if (!operation || !description) return null;
  return {
    description,
    operation,
    risk: textField(proposal, "risk") || "critical",
    service: textField(proposal, "service") || null,
  };
}

export function applyGatewayEvent(state: ArcenalChatState, event: GatewayEventLike): ArcenalChatState {
  if (event.session_id && event.session_id !== state.sessionId) return state;
  if (event.type === "message.start") return { ...state, activity: "ARC analyse votre demande…", busy: true };
  if (event.type === "message.delta") return { ...state, streamingText: state.streamingText + textField(event.payload, "text") };
  if (event.type === "message.complete") return completeMessage(state, event.payload);
  if (event.type === "status.update") return { ...state, activity: textField(event.payload, "text") };
  if (event.type === "tool.start") return { ...state, activity: `Action : ${textField(event.payload, "name")}` };
  if (event.type === "tool.complete") return { ...state, pendingMaintenance: maintenance(event.payload) ?? state.pendingMaintenance };
  if (event.type === "approval.request") return { ...state, pendingApproval: approval(event.payload) };
  if (event.type === "error") {
    const error = providerErrorMessage(textField(event.payload, "message"));
    return { ...state, activity: "", busy: false, error, streamingText: "" };
  }
  return state;
}

interface SessionSnapshot {
  inflight?: unknown;
  messages?: unknown[];
  running?: boolean;
}

function settleFromSnapshot(state: ArcenalChatState, snapshot: SessionSnapshot, failure: string): ArcenalChatState {
  return {
    ...state,
    activity: "",
    busy: false,
    error: failure || state.error,
    messages: normalizeHistory(snapshot.messages ?? state.messages),
    streamingText: "",
  };
}

export function synchronizeChat(state: ArcenalChatState, snapshot: SessionSnapshot): ArcenalChatState {
  if (!state.busy) return state;
  const inflight = record(snapshot.inflight);
  const rawFailure = textField(inflight, "error");
  const failure = rawFailure ? providerErrorMessage(rawFailure) : "";
  if (!snapshot.running) return settleFromSnapshot(state, snapshot, failure);
  return {
    ...state,
    activity: "ARC analyse votre demande…",
    error: failure,
    streamingText: textField(inflight, "assistant") || state.streamingText,
  };
}

export function normalizeHistory(history: unknown[]): ArcenalChatMessage[] {
  return history.flatMap((item, index) => {
    const entry = record(item);
    const role = entry.role;
    const text = typeof entry.text === "string" ? entry.text.trim() : "";
    if ((role !== "user" && role !== "assistant") || !text) return [];
    return [{ id: `history-${index}`, role, text }];
  });
}

export function canSubmitMessage(text: string, connection: ChatConnectionState, busy: boolean): boolean {
  return text.trim().length > 0 && connection === "open" && !busy;
}

export function completeMaintenance(state: ArcenalChatState, operation: string): ArcenalChatState {
  const message = assistantMessage(`L’action administrative « ${operation} » a été exécutée et journalisée.`);
  return { ...state, error: "", messages: [...state.messages, message], pendingMaintenance: null };
}
