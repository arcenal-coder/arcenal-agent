import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, type ProfileInfo, type SkillInfo, type ToolsetInfo } from "./api";
import { createSpecializedAgent, loadSpecializedAgent, saveSpecializedAgent } from "./arcenal-agent-service";
import { emptyAgentDraft } from "./arcenal-agents";

vi.mock("./api", () => ({
  api: {
    createProfile: vi.fn(), deleteProfile: vi.fn(), getArcenalAgentMemory: vi.fn(),
    getAuxiliaryModels: vi.fn(), getModelOptions: vi.fn(), getProfileSoul: vi.fn(),
    getSkills: vi.fn(), getToolsets: vi.fn(), saveArcenalAgentMemory: vi.fn(),
    setModelAssignment: vi.fn(), setProfileModel: vi.fn(), toggleSkill: vi.fn(),
    toggleToolset: vi.fn(), updateProfileDescription: vi.fn(), updateProfileSoul: vi.fn(),
  },
}));

const SKILLS: SkillInfo[] = [{ category: "arc", description: "", enabled: true, name: "rag" }];
const TOOLS: ToolsetInfo[] = [{ configured: true, description: "", enabled: false, label: "Web", name: "web", platform: "arc", platform_label: "ARC", tools: [] }];
const PROFILE = { description: "Veiller", is_default: false, model: "main", name: "veille", provider: "openai" } as ProfileInfo;

describe("administration des agents spécialisés", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getModelOptions).mockResolvedValue({ provider: "openai", providers: [] });
    vi.mocked(api.getSkills).mockResolvedValue(SKILLS);
    vi.mocked(api.getToolsets).mockResolvedValue(TOOLS);
    vi.mocked(api.getProfileSoul).mockResolvedValue({ content: "# Identité\n\nAnalyste\n\n# Mission\n\nVeiller", exists: true });
    vi.mocked(api.getArcenalAgentMemory).mockResolvedValue({ content: "Mémoire", profile: "veille", updated_at: null });
    vi.mocked(api.getAuxiliaryModels).mockResolvedValue({ main: { model: "main", provider: "openai" }, tasks: [{ base_url: "", model: "small", provider: "openai", task: "" }] });
  });

  it("charge une fiche isolée avec ses permissions effectives", async () => {
    const result = await loadSpecializedAgent(PROFILE);
    expect(result.draft.identity).toBe("Analyste");
    expect(result.draft.skills).toEqual(["rag"]);
    expect(result.draft.toolsets).toEqual([]);
  });

  it("crée et spécialise un agent nominal", async () => {
    const draft = { ...emptyAgentDraft("openai"), mainModel: "main", mission: "Veiller", name: "veille", skills: ["rag"], toolsets: ["web"] };
    await createSpecializedAgent(draft);
    expect(api.createProfile).toHaveBeenCalledWith(expect.objectContaining({ name: "veille" }));
    expect(api.toggleToolset).toHaveBeenCalledWith("web", true, "veille");
  });

  it("réinitialise le modèle secondaire lorsqu’il est vidé", async () => {
    const draft = { ...emptyAgentDraft("openai"), mainModel: "main", mission: "Veiller", name: "veille", skills: ["rag"] };
    await saveSpecializedAgent(draft, { models: {}, skills: SKILLS, toolsets: TOOLS });
    expect(api.setModelAssignment).toHaveBeenCalledWith(expect.objectContaining({ task: "__reset__" }), "veille");
  });

  it("rejette un agent sans mission avant tout appel réseau", async () => {
    await expect(createSpecializedAgent({ ...emptyAgentDraft(), mainModel: "main", name: "veille" })).rejects.toThrow("mission");
    expect(api.createProfile).not.toHaveBeenCalled();
  });
});
