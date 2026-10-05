import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchJSON, type ArcenalModelDescriptor } from "./api";
import { authorizeModelForAgent, buildAgentModelPolicy, createManagedAgent, loadManagedAgents, modelMeetsAgentPrivacy, modelsForAgent, modelsForPrivacy, modelsForProvider, requiredAgentPrivacy, selectableModels, updateManagedAgent, type ManagedAgent } from "./arcenal-agent-manager";

vi.mock("./api", () => ({ fetchJSON: vi.fn() }));

const MODELS: ArcenalModelDescriptor[] = [
  { id: "public-model", provider: "openrouter", model_name: "public", display_name: "Public", enabled: true, availability: "available", catalog_source: "configured", capabilities: ["standard"], context_window: null, supports_tools: false, supports_structured_output: false, supports_vision: false, privacy_class: "public", location: "remote", hosting_region: null, input_cost: 0, output_cost: 0, priority: 30 },
  { id: "gemini-flash", provider: "gemini", model_name: "gemini-flash", display_name: "Gemini Flash", enabled: true, availability: "available", catalog_source: "discovered", capabilities: ["standard"], context_window: null, supports_tools: true, supports_structured_output: true, supports_vision: false, privacy_class: "internal", location: "remote", hosting_region: null, input_cost: 0, output_cost: 0, priority: 10 },
  { id: "gemini-disabled", provider: "gemini", model_name: "gemini-disabled", display_name: "Gemini désactivé", enabled: false, availability: "available", catalog_source: "configured", capabilities: ["standard"], context_window: null, supports_tools: false, supports_structured_output: false, supports_vision: false, privacy_class: "internal", location: "remote", hosting_region: null, input_cost: 0, output_cost: 0, priority: 20 },
  { id: "ollama-local", provider: "ollama", model_name: "qwen3:8b", display_name: "Qwen local", enabled: true, availability: "available", catalog_source: "discovered", capabilities: ["standard"], context_window: null, supports_tools: true, supports_structured_output: false, supports_vision: false, privacy_class: "internal", location: "local", hosting_region: null, input_cost: 0, output_cost: 0, priority: 5 },
  { id: "openrouter-admin", provider: "openrouter", model_name: "admin", display_name: "Administration", enabled: true, availability: "available", catalog_source: "configured", capabilities: ["standard"], context_window: null, supports_tools: true, supports_structured_output: true, supports_vision: false, privacy_class: "admin", location: "remote", hosting_region: null, input_cost: 0, output_cost: 0, priority: 1 },
];

const ARC_AGENT: ManagedAgent = {
  application: "arcenal-system", autonomy_level: "approval_required", description: "Architecte", enabled: true,
  harness: { context: "", directives: "", memory: "" }, id: "arc", knowledge_scopes: ["system"], metadata: {},
  model_policy: { allowed_models: [], allowed_providers: [], denied_providers: [], local_only: false, local_preferred: true, mode: "auto" },
  name: "ARC", permissions: ["system.admin"], role: "architect", system_instructions: [], tools: [],
};

describe("registre ARC Core", () => {
  beforeEach(() => vi.clearAllMocks());

  it("charge les agents gouvernés", async () => {
    vi.mocked(fetchJSON).mockResolvedValue({ agents: [{ id: "arc" }, { id: "ats" }] });
    await expect(loadManagedAgents()).resolves.toHaveLength(2);
  });

  it("persiste uniquement les réglages sûrs", async () => {
    vi.mocked(fetchJSON).mockResolvedValue({ id: "ats", enabled: false });
    await updateManagedAgent("ats", { autonomy_level: "controlled", enabled: false });
    expect(fetchJSON).toHaveBeenCalledWith(expect.stringContaining("/ats"), expect.objectContaining({ method: "PATCH" }));
  });

  it("crée un agent gouverné via le registre ARC", async () => {
    vi.mocked(fetchJSON).mockResolvedValue({ id: "veille" });
    const agent: ManagedAgent = {
      application: "arcenal-system", autonomy_level: "controlled", description: "Veille",
      enabled: true, harness: { context: "Contexte", directives: "Directives", memory: "" }, id: "veille", knowledge_scopes: ["regulatory"], metadata: {},
      model_policy: { allowed_models: [], allowed_providers: [], denied_providers: [], local_only: false, local_preferred: true, mode: "auto" },
      name: "Veille", permissions: [], role: "analyst", system_instructions: [{ content: "Veiller", id: "mission" }], tools: [],
    };
    await createManagedAgent(agent);
    expect(fetchJSON).toHaveBeenCalledWith(expect.stringContaining("registry"), expect.objectContaining({ method: "POST" }));
  });

  it("met à jour le harnais propre à un agent", async () => {
    vi.mocked(fetchJSON).mockResolvedValue({ id: "ats" });
    const harness = { context: "Contexte ATS", directives: "Directives ATS", memory: "Mémoire ATS" };

    await updateManagedAgent("ats", { harness });

    expect(fetchJSON).toHaveBeenCalledWith(expect.stringContaining("/ats"), expect.objectContaining({ body: JSON.stringify({ harness }) }));
  });

  it("construit une politique automatique sans pseudo-modèle", () => {
    expect(buildAgentModelPolicy("auto", "", "", false, true, MODELS)).toEqual({
      allowed_models: [], allowed_providers: [], denied_providers: [], local_only: false, local_preferred: true, mode: "auto",
    });
  });

  it("construit une politique fixe depuis le registre", () => {
    expect(buildAgentModelPolicy("fixed", "gemini", "gemini-flash", false, true, MODELS)).toMatchObject({
      allowed_models: ["gemini-flash"], allowed_providers: ["gemini"], mode: "fixed",
    });
  });

  it("préserve les contraintes de routage lors d’un changement de modèle", () => {
    const current = { allowed_models: [], allowed_providers: [], denied_providers: ["openai"], local_only: false, local_preferred: true, max_cost: 0.2, mode: "auto" as const, preferred_capability: "light" as const };
    const policy = buildAgentModelPolicy("fixed", "gemini", "gemini-flash", false, true, MODELS, current);

    expect(policy).toMatchObject({ denied_providers: ["openai"], max_cost: 0.2, preferred_capability: "light" });
  });

  it("refuse un modèle absent, désactivé ou distant pour local_only", () => {
    expect(() => buildAgentModelPolicy("fixed", "gemini", "auto", false, true, MODELS)).toThrow(/registre/);
    expect(() => buildAgentModelPolicy("fixed", "gemini", "gemini-disabled", false, true, MODELS)).toThrow(/activé/);
    expect(() => buildAgentModelPolicy("fixed", "gemini", "gemini-flash", true, true, MODELS)).toThrow(/local/);
  });

  it("filtre les modèles activés et disponibles par fournisseur", () => {
    expect(modelsForProvider(MODELS, "gemini").map((model) => model.id)).toEqual(["gemini-flash"]);
  });

  it("exclut les modèles incompatibles avec la confidentialité de l’agent", () => {
    expect(requiredAgentPrivacy(ARC_AGENT)).toBe("admin");
    expect(modelsForAgent(MODELS, ARC_AGENT).map((model) => model.id)).toEqual(["openrouter-admin"]);
  });

  it("garde les fournisseurs disponibles visibles avant leur autorisation", () => {
    expect(selectableModels(MODELS, false).map((model) => model.provider)).toContain("gemini");
    expect(modelMeetsAgentPrivacy(MODELS[1], ARC_AGENT)).toBe(false);
  });

  it("autorise explicitement un modèle au niveau requis par l’agent", () => {
    const authorized = authorizeModelForAgent(MODELS[1], ARC_AGENT);

    expect(authorized).toMatchObject({ id: "gemini-flash", privacy_class: "admin" });
    expect(MODELS[1].privacy_class).toBe("internal");
  });

  it("conserve le niveau interne pour un agent sans permission sensible", () => {
    const agent = { ...ARC_AGENT, permissions: [] };
    expect(requiredAgentPrivacy(agent)).toBe("internal");
    expect(modelsForAgent([], agent)).toEqual([]);
  });

  it("écarte les modèles publics lors de la création d’un agent", () => {
    expect(modelsForPrivacy(MODELS, "internal").map((model) => model.id)).not.toContain("public-model");
  });
});
