import { describe, expect, it } from "vitest";
import { isProviderStatusesResponse } from "./arcenal-provider-status";

describe("contrat des états fournisseurs ARC", () => {
  it("accepte un état complet", () => {
    const probe = { configured: true, connection: "connected", message: "Connexion opérationnelle.", models: ["model-a"], provider: "openai", tested_at: "2026-09-28T12:00:00Z" };
    expect(isProviderStatusesResponse({ providers: { openai: probe } })).toBe(true);
  });

  it("accepte l’absence de test antérieur", () => {
    expect(isProviderStatusesResponse({ providers: {} })).toBe(true);
  });

  it("accepte un quota fournisseur limité comme état distinct", () => {
    const probe = { configured: true, connection: "quota_limited", message: "Quota épuisé", models: [], provider: "gemini", tested_at: "2026-10-02T08:00:00Z" };
    expect(isProviderStatusesResponse({ providers: { gemini: probe } })).toBe(true);
  });

  it("refuse un secret ou un état incomplet à la frontière", () => {
    expect(isProviderStatusesResponse({ providers: { openai: { api_key: "secret" } } })).toBe(false);
    expect(isProviderStatusesResponse(null)).toBe(false);
  });
});
