import type { AutonomyLevel } from "./arcenal-providers";

export type AccessCredentialKind = "account" | "api";

export interface AccessCredential {
  autonomy: AutonomyLevel;
  id: string;
  kind: AccessCredentialKind;
  label: string;
  login?: string;
  secretEnv: string;
  serviceUrl: string;
}

export interface AccessCredentialDraft {
  autonomy: AutonomyLevel;
  kind: AccessCredentialKind;
  label: string;
  login: string;
  secret: string;
  serviceUrl: string;
}

const VALID_AUTONOMY = new Set<AutonomyLevel>(["manual", "smart", "off"]);

export class AccessCredentialError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "AccessCredentialError";
  }
}

export function accessCredentialsFromConfig(config: Record<string, unknown>): AccessCredential[] {
  const arcenal = recordValue(config.arcenal);
  const raw = arcenal?.access_credentials;
  if (!Array.isArray(raw)) return [];
  return raw.map(parseCredential).filter((item): item is AccessCredential => item !== null);
}

export function createAccessCredential(draft: AccessCredentialDraft, existing: AccessCredential[]): AccessCredential {
  const label = draft.label.trim();
  const serviceUrl = normalizeServiceUrl(draft.serviceUrl);
  if (!label || !draft.secret.trim()) throw new AccessCredentialError("Le nom et le secret sont obligatoires.");
  if (draft.kind === "account" && !draft.login.trim()) throw new AccessCredentialError("Le login est obligatoire pour un compte.");
  const id = uniqueCredentialId(label, existing);
  return { autonomy: draft.autonomy, id, kind: draft.kind, label, login: draft.kind === "account" ? draft.login.trim() : undefined, secretEnv: secretEnvName(id, draft.kind), serviceUrl };
}

export function secretEnvName(id: string, kind: AccessCredentialKind): string {
  return `ARCENAL_ACCESS_${id.toUpperCase()}_${kind === "api" ? "API_KEY" : "PASSWORD"}`;
}

function parseCredential(value: unknown): AccessCredential | null {
  const item = recordValue(value);
  if (!item || !isKind(item.kind) || !isText(item.id) || !isText(item.label) || !isSecretEnv(item.secretEnv) || !isText(item.serviceUrl)) return null;
  const autonomy = VALID_AUTONOMY.has(item.autonomy as AutonomyLevel) ? item.autonomy as AutonomyLevel : "manual";
  const login = isText(item.login) ? item.login : undefined;
  return { autonomy, id: item.id, kind: item.kind, label: item.label, login, secretEnv: item.secretEnv, serviceUrl: item.serviceUrl };
}

function uniqueCredentialId(label: string, existing: AccessCredential[]): string {
  const base = label.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "acces";
  const used = new Set(existing.map((item) => item.id));
  if (!used.has(base)) return base;
  let suffix = 2;
  while (used.has(`${base}_${suffix}`)) suffix += 1;
  return `${base}_${suffix}`;
}

function normalizeServiceUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) throw new AccessCredentialError("L’adresse du service est obligatoire.");
  const url = parseUrl(trimmed);
  if (!["http:", "https:"].includes(url.protocol)) throw new AccessCredentialError("L’adresse doit utiliser HTTP ou HTTPS.");
  if (url.username || url.password) throw new AccessCredentialError("L’adresse ne doit pas contenir d’identifiants.");
  return url.toString();
}

function parseUrl(value: string): URL {
  try {
    return new URL(value);
  } catch (cause) {
    throw new AccessCredentialError("L’adresse du service n’est pas valide.", { cause });
  }
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function isKind(value: unknown): value is AccessCredentialKind {
  return value === "account" || value === "api";
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isSecretEnv(value: unknown): value is string {
  return isText(value) && /^ARCENAL_ACCESS_[A-Z0-9_]+_(API_KEY|PASSWORD)$/.test(value);
}
