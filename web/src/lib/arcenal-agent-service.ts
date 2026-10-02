import {
  api,
  type ModelOptionsResponse,
  type ProfileInfo,
  type SkillInfo,
  type ToolsetInfo,
} from "./api";
import {
  agentSoul,
  extractAgentIdentity,
  secondaryAssignment,
  validateAgentDraft,
  type AgentDraft,
} from "./arcenal-agents";

export interface AgentCatalog {
  models: ModelOptionsResponse;
  skills: SkillInfo[];
  toolsets: ToolsetInfo[];
}

export interface LoadedAgent {
  catalog: AgentCatalog;
  draft: AgentDraft;
}

export class AgentProvisionError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "AgentProvisionError";
  }
}

export async function loadAgentCatalog(profile?: string): Promise<AgentCatalog> {
  const [models, skills, toolsets] = await Promise.all([
    api.getModelOptions(profile),
    api.getSkills(profile),
    api.getToolsets(profile),
  ]);
  return { models, skills, toolsets };
}

export async function loadSpecializedAgent(profile: ProfileInfo): Promise<LoadedAgent> {
  const [catalog, soul, harness, auxiliary] = await Promise.all([
    loadAgentCatalog(profile.name),
    api.getProfileSoul(profile.name),
    api.getArcenalAgentHarness(profile.name),
    api.getAuxiliaryModels(profile.name),
  ]);
  const secondary = secondaryAssignment(auxiliary);
  const draft = draftFromProfile(profile, soul.content, harness, secondary.model);
  return { catalog, draft: withEnabledCapabilities(draft, catalog) };
}

export async function createSpecializedAgent(draft: AgentDraft): Promise<void> {
  const clean = validateAgentDraft(draft);
  await api.createProfile(createPayload(clean));
  try {
    await persistAgentIdentity(clean);
    const catalog = await loadAgentCatalog(clean.name);
    await synchronizeCapabilities(clean, catalog);
  } catch (cause) {
    throw new AgentProvisionError("L’agent a été créé, mais sa spécialisation reste incomplète.", { cause });
  }
}

export async function saveSpecializedAgent(draft: AgentDraft, catalog: AgentCatalog): Promise<void> {
  const clean = validateAgentDraft(draft);
  await Promise.all([
    api.updateProfileDescription(clean.name, clean.mission),
    api.setProfileModel(clean.name, clean.provider, clean.mainModel),
    api.updateProfileSoul(clean.name, agentSoul(clean)),
    api.saveArcenalAgentHarness(clean.name, agentHarness(clean)),
    saveSecondaryModel(clean),
  ]);
  await synchronizeCapabilities(clean, catalog);
}

function createPayload(draft: AgentDraft): Parameters<typeof api.createProfile>[0] {
  return {
    description: draft.mission,
    keep_skills: draft.skills,
    model: draft.mainModel,
    name: draft.name,
    provider: draft.provider,
  };
}

async function persistAgentIdentity(draft: AgentDraft): Promise<void> {
  await Promise.all([
    api.updateProfileSoul(draft.name, agentSoul(draft)),
    api.saveArcenalAgentHarness(draft.name, agentHarness(draft)),
    saveSecondaryModel(draft),
  ]);
}

async function saveSecondaryModel(draft: AgentDraft): Promise<void> {
  const reset = draft.secondaryModel ? "" : "__reset__";
  await api.setModelAssignment({
    model: draft.secondaryModel,
    provider: draft.provider,
    scope: "auxiliary",
    task: reset,
  }, draft.name);
}

async function synchronizeCapabilities(draft: AgentDraft, catalog: AgentCatalog): Promise<void> {
  await Promise.all([
    synchronizeSkills(draft.name, draft.skills, catalog.skills),
    synchronizeToolsets(draft.name, draft.toolsets, catalog.toolsets),
  ]);
}

async function synchronizeSkills(profile: string, selected: string[], catalog: SkillInfo[]): Promise<void> {
  const changes = catalog.filter((skill) => skill.enabled !== selected.includes(skill.name));
  await Promise.all(changes.map((skill) => api.toggleSkill(skill.name, selected.includes(skill.name), profile)));
}

async function synchronizeToolsets(profile: string, selected: string[], catalog: ToolsetInfo[]): Promise<void> {
  const changes = catalog.filter((toolset) => toolset.enabled !== selected.includes(toolset.name));
  await Promise.all(changes.map((toolset) => api.toggleToolset(toolset.name, selected.includes(toolset.name), profile)));
}

function agentHarness(draft: AgentDraft): { context: string; directives: string; memory: string } {
  return { context: draft.context, directives: draft.directives, memory: draft.memory };
}

function draftFromProfile(profile: ProfileInfo, soul: string, harness: { context: string; directives: string; memory: string }, secondaryModel: string): AgentDraft {
  return {
    context: harness.context,
    directives: harness.directives,
    identity: extractAgentIdentity(soul),
    mainModel: profile.model ?? "",
    memory: harness.memory,
    mission: profile.description,
    name: profile.name,
    provider: profile.provider ?? "openrouter",
    secondaryModel,
    skills: [],
    toolsets: [],
  };
}

function withEnabledCapabilities(draft: AgentDraft, catalog: AgentCatalog): AgentDraft {
  return {
    ...draft,
    skills: catalog.skills.filter((skill) => skill.enabled).map((skill) => skill.name),
    toolsets: catalog.toolsets.filter((toolset) => toolset.enabled).map((toolset) => toolset.name),
  };
}
