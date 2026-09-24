import { describe, expect, it } from "vitest";
import { connectionLabel, openRouterModelSelection } from "@/lib/arcenal-openrouter";

describe("openRouterModelSelection", () => {
  it("conserve le modèle OpenRouter actif", () => {
    const result = openRouterModelSelection({
      provider: "openrouter",
      model: "mistral/large",
      providers: [{ name: "OpenRouter", slug: "openrouter", models: ["openai/gpt", "mistral/large"] }],
    });

    expect(result).toEqual({ current: "mistral/large", models: ["openai/gpt", "mistral/large"] });
  });

  it("retire les doublons et choisit le premier modèle disponible", () => {
    const result = openRouterModelSelection({
      provider: "anthropic",
      model: "claude",
      providers: [{ name: "OpenRouter", slug: "openrouter", models: ["openai/gpt", "openai/gpt", ""] }],
    });

    expect(result).toEqual({ current: "openai/gpt", models: ["openai/gpt"] });
  });

  it("reste vide lorsque le fournisseur est absent", () => {
    expect(openRouterModelSelection({ providers: [] })).toEqual({ current: "", models: [] });
  });
});

describe("connectionLabel", () => {
  it("traduit les états sans exposer de détail technique", () => {
    expect(connectionLabel(null)).toBe("État non vérifié");
    expect(connectionLabel({ configured: true, connection: "connected", message: "ok" })).toBe("Connecté");
    expect(connectionLabel({ configured: true, connection: "invalid", message: "ko" })).toBe("Clé refusée");
  });
});
