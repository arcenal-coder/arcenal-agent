import { fetchJSON } from "./api";

export type AgentAutonomy = "automatic" | "controlled" | "approval_required";

export interface ManagedAgent {
  application: string;
  autonomy_level: AgentAutonomy;
  description: string;
  enabled: boolean;
  id: string;
  knowledge_scopes: string[];
  metadata: Record<string, string>;
  model_policy: { allowed_models: string[]; allowed_providers: string[]; local_preferred: boolean; mode: "auto" | "fixed" };
  name: string;
  permissions: string[];
  role: string;
  system_instructions: { content: string; id: string }[];
  tools: string[];
}

export interface ManagedAgentUpdate {
  autonomy_level?: AgentAutonomy;
  enabled?: boolean;
}

const REGISTRY_URL = "/api/plugins/arcenal-supervisor/agents/registry";

export async function loadManagedAgents(): Promise<ManagedAgent[]> {
  const result = await fetchJSON<{ agents: ManagedAgent[] }>(REGISTRY_URL);
  return result.agents;
}

export async function updateManagedAgent(agentId: string, update: ManagedAgentUpdate): Promise<ManagedAgent> {
  return fetchJSON<ManagedAgent>(`${REGISTRY_URL}/${encodeURIComponent(agentId)}`, {
    body: JSON.stringify(update),
    headers: { "Content-Type": "application/json" },
    method: "PATCH",
  });
}
