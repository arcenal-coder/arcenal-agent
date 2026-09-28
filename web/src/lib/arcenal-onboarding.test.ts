import { describe, expect, it } from "vitest";
import type { ArcenalProviderStatusesResponse, ArcenalSecurityOverview, ArcenalSystemOverview } from "./api";
import { onboardingChecks, onboardingCompleted, requiredChecksPass } from "./arcenal-onboarding";

const security = { actor: { username: "admin", roles: ["admins"] }, gateways: { control: true, readonly: true } } as ArcenalSecurityOverview;
const system = { health: "healthy", platform: { hostname: "arcenal", yunohost: true, versions: { yunohost: "12.1" } } } as ArcenalSystemOverview;
const providers = { providers: { openrouter: { configured: true, connection: "connected" } } } as ArcenalProviderStatusesResponse;

describe("premier démarrage ARCenal", () => {
  it("reconnaît une initialisation persistée", () => {
    expect(onboardingCompleted({ arcenal: { onboarding: { completed: true } } })).toBe(true);
  });

  it("valide les prérequis et laisse le fournisseur optionnel", () => {
    const checks = onboardingChecks(security, system, { providers: {} });
    expect(requiredChecksPass(checks)).toBe(true);
    expect(checks.find((check) => check.id === "provider")?.ok).toBe(false);
  });

  it("bloque la finalisation si une passerelle privilégiée manque", () => {
    const broken = { ...security, gateways: { control: false, readonly: true } };
    expect(requiredChecksPass(onboardingChecks(broken, system, providers))).toBe(false);
  });
});
