import { describe, expect, it } from "vitest";
import { autonomyFromConfig, buildProviderConnections, normalizeCustomEnvKey } from "@/lib/arcenal-providers";

describe("connexions LLM ARC", () => {
  it("conserve plusieurs fournisseurs configurés simultanément", () => {
    const connections = buildProviderConnections({
      ANTHROPIC_API_KEY: { is_set: true },
      GEMINI_API_KEY: { is_set: true },
      OPENAI_API_KEY: { is_set: false },
    });

    expect(connections.filter((item) => item.configured).map((item) => item.id)).toEqual(["anthropic", "gemini"]);
  });

  it("reconnaît Ollama sans exiger de clé API", () => {
    const connections = buildProviderConnections({}, { ollama: { base_url: "http://127.0.0.1:11434/v1" } });
    expect(connections.find((item) => item.id === "ollama")).toMatchObject({ configured: true, keyRequired: false });
  });

  it("valide le nom d’une clé personnalisée", () => {
    expect(normalizeCustomEnvKey(" ma-cle api ")).toBe("MA_CLE_API");
    expect(normalizeCustomEnvKey("PATH")).toBe("");
  });

  it("revient au niveau prudent si la configuration est invalide", () => {
    expect(autonomyFromConfig({ approvals: { mode: "smart" } })).toBe("smart");
    expect(autonomyFromConfig({ approvals: { mode: "inconnu" } })).toBe("manual");
  });
});
