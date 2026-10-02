import type { AuxiliaryModelsResponse, ProfileInfo } from "./api";

export interface AgentDraft {
  context: string;
  directives: string;
  identity: string;
  mainModel: string;
  memory: string;
  mission: string;
  name: string;
  provider: string;
  secondaryModel: string;
  skills: string[];
  toolsets: string[];
}

export class AgentDraftError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AgentDraftError";
  }
}

export function emptyAgentDraft(provider = "openrouter"): AgentDraft {
  return { context: "", directives: "", identity: "", mainModel: "", memory: "", mission: "", name: "", provider, secondaryModel: "", skills: [], toolsets: [] };
}

export function validateAgentDraft(draft: AgentDraft): AgentDraft {
  const name = normalizeAgentName(draft.name);
  if (!name) throw new AgentDraftError("L’identifiant de l’agent est obligatoire.");
  if (!draft.mission.trim()) throw new AgentDraftError("La mission de l’agent est obligatoire.");
  if (!draft.provider.trim() || !draft.mainModel.trim()) throw new AgentDraftError("Le fournisseur et le modèle principal sont obligatoires.");
  return { ...draft, context: draft.context.trim(), directives: draft.directives.trim(), identity: draft.identity.trim(), mainModel: draft.mainModel.trim(), memory: draft.memory.trim(), mission: draft.mission.trim(), name, provider: draft.provider.trim(), secondaryModel: draft.secondaryModel.trim(), skills: unique(draft.skills), toolsets: unique(draft.toolsets) };
}

export function specializedProfiles(profiles: ProfileInfo[]): ProfileInfo[] {
  return profiles.filter((profile) => !profile.is_default && profile.name !== "default");
}

export function secondaryAssignment(models: AuxiliaryModelsResponse): { model: string; provider: string } {
  const assignment = models.tasks.find((item) => item.task === "") ?? models.tasks[0];
  return assignment ? { model: assignment.model, provider: assignment.provider } : { model: "", provider: models.main.provider };
}

export function agentSoul(draft: Pick<AgentDraft, "identity" | "mission">): string {
  const identity = draft.identity || "Agent spécialisé ARCenal";
  return `# Identité\n\n${identity}\n\n# Mission\n\n${draft.mission}\n\n# Gouvernance\n\nRespecter les permissions, demander confirmation pour toute action sensible et ne jamais exposer de secret.`;
}

export function extractAgentIdentity(soul: string): string {
  const match = soul.match(/^# Identité\s+([\s\S]*?)(?=\n# Mission|$)/u);
  return match?.[1]?.trim() ?? soul.trim();
}

function normalizeAgentName(value: string): string {
  return value.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64);
}

function unique(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}
