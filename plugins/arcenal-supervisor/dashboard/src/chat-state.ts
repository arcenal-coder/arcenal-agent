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

export interface ArcenalChatState {
  activity: string;
  busy: boolean;
  error: string;
  messages: ArcenalChatMessage[];
  pendingApproval: PendingApproval | null;
  sessionId: string;
  storedSessionId: string;
  streamingText: string;
}

export interface GatewayEventLike {
  payload?: unknown;
  session_id?: string;
  type: string;
}

type UnknownRecord = Record<string, unknown>;

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

function completeMessage(state: ArcenalChatState, payload: unknown): ArcenalChatState {
  const data = record(payload);
  const text = textField(data, "text") || state.streamingText;
  const messages = text ? [...state.messages, assistantMessage(text)] : state.messages;
  const error = data.status === "error" ? textField(data, "error") || text : "";
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

export function applyGatewayEvent(state: ArcenalChatState, event: GatewayEventLike): ArcenalChatState {
  if (event.session_id && event.session_id !== state.sessionId) return state;
  if (event.type === "message.start") return { ...state, activity: "ARC analyse votre demande…", busy: true };
  if (event.type === "message.delta") return { ...state, streamingText: state.streamingText + textField(event.payload, "text") };
  if (event.type === "message.complete") return completeMessage(state, event.payload);
  if (event.type === "status.update") return { ...state, activity: textField(event.payload, "text") };
  if (event.type === "tool.start") return { ...state, activity: `Action : ${textField(event.payload, "name")}` };
  if (event.type === "approval.request") return { ...state, pendingApproval: approval(event.payload) };
  if (event.type === "error") return { ...state, busy: false, error: textField(event.payload, "message") || "La réponse d’ARC a échoué." };
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
  const failure = textField(inflight, "error");
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
