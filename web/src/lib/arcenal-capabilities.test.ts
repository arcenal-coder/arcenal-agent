import { describe, expect, it } from "vitest";
import type { ArcenalCapabilitiesResponse, ToolsetInfo } from "./api";
import { capabilityViews, isCapabilitiesResponse } from "./arcenal-capabilities";

const RESPONSE: ArcenalCapabilitiesResponse = {
  capabilities: [{ confirmation: false, description: "Lire le système", enabled: true, last_usage: null, mutable: false, name: "arcenal_system_status", origin: "arcenal", permission: "Lecture système", risk: "none" }],
  usage: { terminal: { count: 2, duration_ms: 50, last_status: "success", last_used: "2026-09-28T12:00:00+00:00" } },
};

const TOOLSET: ToolsetInfo = { configured: true, description: "Exécuter des commandes", enabled: false, label: "Terminal", name: "terminal", platform: "cli", platform_label: "CLI", tools: ["terminal"] };

describe("inventaire des capacités ARC", () => {
  it("valide une réponse complète et refuse un risque inconnu", () => {
    expect(isCapabilitiesResponse(RESPONSE)).toBe(true);
    expect(isCapabilitiesResponse({ ...RESPONSE, capabilities: [{ ...RESPONSE.capabilities[0], risk: "critical" }] })).toBe(false);
  });

  it("distingue les capacités ARC des capacités Hermes", () => {
    const views = capabilityViews(RESPONSE, [TOOLSET]);

    expect(views.map((item) => item.origin)).toEqual(["arcenal", "hermes"]);
    expect(views[1]).toMatchObject({ confirmation: true, lastUsage: RESPONSE.usage.terminal, risk: "high" });
  });

  it("accepte un inventaire vide", () => {
    expect(capabilityViews({ capabilities: [], usage: {} }, [])).toEqual([]);
  });
});
