export type AutonomyLevel = "manual" | "smart" | "off";

export interface ProviderConnection {
  configured: boolean;
  configurableUrl: boolean;
  defaultBaseUrl: string;
  enabled: boolean;
  envKey: string;
  id: string;
  keyRequired: boolean;
  label: string;
  local: boolean;
}

interface EnvStatus { is_set?: boolean }
type ProviderConfig = Record<string, { base_url?: unknown; enabled?: unknown }>;

const PROVIDERS = [
  { configurableUrl: false, defaultBaseUrl: "https://openrouter.ai/api/v1", envKey: "OPENROUTER_API_KEY", id: "openrouter", keyRequired: true, label: "OpenRouter", local: false },
  { configurableUrl: false, defaultBaseUrl: "https://api.openai.com/v1", envKey: "OPENAI_API_KEY", id: "openai", keyRequired: true, label: "OpenAI", local: false },
  { configurableUrl: false, defaultBaseUrl: "https://api.anthropic.com/v1", envKey: "ANTHROPIC_API_KEY", id: "anthropic", keyRequired: true, label: "Anthropic", local: false },
  { configurableUrl: false, defaultBaseUrl: "https://api.mistral.ai/v1", envKey: "MISTRAL_API_KEY", id: "mistral", keyRequired: true, label: "Mistral", local: false },
  { configurableUrl: false, defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta", envKey: "GEMINI_API_KEY", id: "gemini", keyRequired: true, label: "Google Gemini", local: false },
  { configurableUrl: true, defaultBaseUrl: "http://127.0.0.1:11434/v1", envKey: "", id: "ollama", keyRequired: false, label: "Ollama", local: true },
  { configurableUrl: true, defaultBaseUrl: "http://127.0.0.1:8000/v1", envKey: "VLLM_API_KEY", id: "vllm", keyRequired: false, label: "vLLM", local: true },
  { configurableUrl: true, defaultBaseUrl: "", envKey: "OPENAI_COMPATIBLE_API_KEY", id: "compatible", keyRequired: true, label: "API compatible OpenAI", local: false },
  { configurableUrl: true, defaultBaseUrl: "", envKey: "ARCENAL_INTERNAL_LLM_API_KEY", id: "internal", keyRequired: true, label: "Fournisseur interne", local: true },
] as const;

export function buildProviderConnections(env: Record<string, EnvStatus>, providers: ProviderConfig = {}): ProviderConnection[] {
  return PROVIDERS.map((provider) => ({
    ...provider,
    configured: provider.keyRequired ? env[provider.envKey]?.is_set === true : typeof providers[provider.id]?.base_url === "string",
    enabled: providers[provider.id]?.enabled !== false,
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
