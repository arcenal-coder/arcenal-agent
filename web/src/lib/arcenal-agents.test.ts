import { describe, expect, it } from "vitest";
import type { ProfileInfo } from "./api";
import { agentSoul, emptyAgentDraft, extractAgentIdentity, secondaryAssignment, specializedProfiles, validateAgentDraft } from "./arcenal-agents";

describe("gouvernance des agents ARCenal", () => {
  it("normalise un agent complet sans doublons de permissions", () => {
    const draft = validateAgentDraft({ ...emptyAgentDraft(), context: "  contexte  ", directives: "  directives  ", identity: "Analyste", mainModel: "gpt-test", memory: "  mémoire  ", mission: "Surveiller la conformité", name: "Veille réglementaire", skills: ["rag", "rag"], toolsets: ["web", "web"] });

    expect(draft.name).toBe("veille-reglementaire");
    expect(draft.skills).toEqual(["rag"]);
    expect(draft.toolsets).toEqual(["web"]);
    expect({ context: draft.context, directives: draft.directives, memory: draft.memory }).toEqual({ context: "contexte", directives: "directives", memory: "mémoire" });
  });

  it("refuse une mission ou un modèle absent", () => {
    expect(() => validateAgentDraft({ ...emptyAgentDraft(), name: "veille" })).toThrow("mission");
    expect(() => validateAgentDraft({ ...emptyAgentDraft(), mission: "Veiller", name: "veille" })).toThrow("modèle principal");
  });

  it("écarte le profil ARC principal", () => {
    const profiles = [{ is_default: true, name: "default" }, { is_default: false, name: "veille" }] as ProfileInfo[];
    expect(specializedProfiles(profiles).map((profile) => profile.name)).toEqual(["veille"]);
  });

  it("construit une identité gouvernée et lit le modèle secondaire", () => {
    const soul = agentSoul({ identity: "Analyste", mission: "Veiller" });
    expect(soul).toContain("demander confirmation");
    expect(extractAgentIdentity(soul)).toBe("Analyste");
    expect(secondaryAssignment({ main: { model: "main", provider: "openai" }, tasks: [{ base_url: "", model: "small", provider: "openai", task: "" }] })).toEqual({ model: "small", provider: "openai" });
  });
});
