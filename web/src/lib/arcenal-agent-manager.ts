import { fetchJSON, type ArcenalModelDescriptor } from "./api";

export type AgentAutonomy = "automatic" | "controlled" | "approval_required";
export type AgentModelMode = "auto" | "fixed";

export interface AgentHarness {
  context: string;
  directives: string;
  memory: string;
}

export interface AgentModelPolicy {
  allowed_models: string[];
  allowed_providers: string[];
  denied_providers: string[];
  local_only: boolean;
  local_preferred: boolean;
  max_cost?: number | null;
  mode: AgentModelMode;
  preferred_capability?: "deterministic" | "light" | "standard" | "advanced" | "specialized";
}

export interface ManagedAgent {
  application: string;
  autonomy_level: AgentAutonomy;
  description: string;
  enabled: boolean;
  harness: AgentHarness;
  id: string;
  knowledge_scopes: string[];
  metadata: Record<string, string>;
  model_policy: AgentModelPolicy;
  name: string;
  permissions: string[];
  role: string;
  system_instructions: { content: string; id: string }[];
  tools: string[];
}

export interface ManagedAgentUpdate {
  autonomy_level?: AgentAutonomy;
  enabled?: boolean;
  harness?: AgentHarness;
  model_policy?: AgentModelPolicy;
}

type PrivacyClass = ArcenalModelDescriptor["privacy_class"];

const PRIVACY_RANK: Readonly<Record<PrivacyClass, number>> = {
  public: 0,
  internal: 1,
  restricted: 2,
  confidential: 3,
  admin: 4,
};

const REGISTRY_URL = "/api/plugins/arcenal-supervisor/agents/registry";

export async function loadManagedAgents(): Promise<ManagedAgent[]> {
  const result = await fetchJSON<{ agents: ManagedAgent[] }>(REGISTRY_URL);
  return result.agents;
}

export async function createManagedAgent(agent: ManagedAgent): Promise<ManagedAgent> {
  return fetchJSON<ManagedAgent>(REGISTRY_URL, {
    body: JSON.stringify(agent),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });
}

export async function updateManagedAgent(agentId: string, update: ManagedAgentUpdate): Promise<ManagedAgent> {
  return fetchJSON<ManagedAgent>(`${REGISTRY_URL}/${encodeURIComponent(agentId)}`, {
    body: JSON.stringify(update),
    headers: { "Content-Type": "application/json" },
    method: "PATCH",
  });
}

export function modelsForProvider(models: ArcenalModelDescriptor[], provider: string): ArcenalModelDescriptor[] {
  return models.filter((model) => (
    model.provider === provider && model.enabled && model.availability !== "unavailable"
  ));
}

export function requiredAgentPrivacy(agent: ManagedAgent): PrivacyClass {
  if (agent.permissions.includes("system.admin")) return "admin";
  if (agent.permissions.includes("knowledge.confidential")) return "confidential";
  if (agent.permissions.includes("knowledge.restricted")) return "restricted";
  return "internal";
}

export function modelsForAgent(models: ArcenalModelDescriptor[], agent: ManagedAgent): ArcenalModelDescriptor[] {
  return modelsForPrivacy(models, requiredAgentPrivacy(agent));
}

export function modelsForPrivacy(models: ArcenalModelDescriptor[], privacy: PrivacyClass): ArcenalModelDescriptor[] {
  const minimum = PRIVACY_RANK[privacy];
  return models.filter((model) => PRIVACY_RANK[model.privacy_class] >= minimum);
}

export function buildAgentModelPolicy(
  mode: AgentModelMode,
  provider: string,
  modelId: string,
  localOnly: boolean,
  localPreferred: boolean,
  models: ArcenalModelDescriptor[],
  current?: AgentModelPolicy,
): AgentModelPolicy {
  if (mode === "auto") return automaticPolicy(localOnly, localPreferred, current);
  const selected = models.find((model) => model.id === modelId && model.provider === provider);
  if (!selected || modelId === "auto") throw new Error("Le modèle doit provenir du registre ARC.");
  if (!selected.enabled || selected.availability === "unavailable") throw new Error("Le modèle sélectionné doit être activé et disponible.");
  if (localOnly && selected.location !== "local") throw new Error("Une politique locale exige un modèle local.");
  return { ...policyBase(localOnly, localPreferred, current), allowed_models: [selected.id], allowed_providers: [provider], mode };
}

function automaticPolicy(localOnly: boolean, localPreferred: boolean, current?: AgentModelPolicy): AgentModelPolicy {
  return { ...policyBase(localOnly, localPreferred, current), allowed_models: [], allowed_providers: [], mode: "auto" };
}

function policyBase(localOnly: boolean, localPreferred: boolean, current?: AgentModelPolicy): AgentModelPolicy {
  return { ...current, allowed_models: [], allowed_providers: [], denied_providers: current?.denied_providers ?? [], local_only: localOnly, local_preferred: localPreferred, mode: "auto" };
}
