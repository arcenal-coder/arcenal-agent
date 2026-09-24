export type AutonomyLevel = "manual" | "smart" | "off";

export interface ProviderConnection {
  configured: boolean;
  envKey: string;
  id: string;
  keyRequired: boolean;
  label: string;
  local: boolean;
}

interface EnvStatus { is_set?: boolean }
type ProviderConfig = Record<string, { base_url?: unknown }>;

const PROVIDERS = [
  { envKey: "OPENROUTER_API_KEY", id: "openrouter", keyRequired: true, label: "OpenRouter", local: false },
  { envKey: "OPENAI_API_KEY", id: "openai", keyRequired: true, label: "OpenAI", local: false },
  { envKey: "ANTHROPIC_API_KEY", id: "anthropic", keyRequired: true, label: "Anthropic", local: false },
  { envKey: "GEMINI_API_KEY", id: "gemini", keyRequired: true, label: "Google Gemini", local: false },
  { envKey: "", id: "ollama", keyRequired: false, label: "Ollama", local: true },
] as const;

export function buildProviderConnections(env: Record<string, EnvStatus>, providers: ProviderConfig = {}): ProviderConnection[] {
  return PROVIDERS.map((provider) => ({
    ...provider,
    configured: provider.keyRequired ? env[provider.envKey]?.is_set === true : typeof providers.ollama?.base_url === "string",
  }));
}

export function normalizeCustomEnvKey(value: string): string {
  const normalized = value.trim().toUpperCase().replace(/[^A-Z0-9_]+/g, "_");
  if (!/^[A-Z_][A-Z0-9_]*$/.test(normalized)) return "";
  return ["HOME", "PATH", "PYTHONPATH", "LD_PRELOAD"].includes(normalized) ? "" : normalized;
}

export function autonomyFromConfig(config: Record<string, unknown>): AutonomyLevel {
  const approvals = config.approvals;
  if (typeof approvals !== "object" || approvals === null) return "manual";
  const mode = (approvals as Record<string, unknown>).mode;
  return mode === "smart" || mode === "off" || mode === "manual" ? mode : "manual";
}
