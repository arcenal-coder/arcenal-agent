import type { ArcenalProviderStatusesResponse, ArcenalSecurityOverview, ArcenalSystemOverview } from "./api";

export interface ArcenalOnboardingCheck {
  detail: string;
  id: "identity" | "gateways" | "system" | "provider";
  label: string;
  ok: boolean;
  required: boolean;
}

export function onboardingCompleted(config: Record<string, unknown>): boolean {
  const arcenal = record(config.arcenal);
  const onboarding = record(arcenal.onboarding);
  return onboarding.completed === true;
}

export function onboardingChecks(security: ArcenalSecurityOverview, system: ArcenalSystemOverview, providers: ArcenalProviderStatusesResponse): ArcenalOnboardingCheck[] {
  const connected = Object.values(providers.providers).filter((provider) => provider.configured && provider.connection === "connected");
  return [
    { id: "identity", label: "Identité administrateur", ok: security.actor.roles.includes("admins"), required: true, detail: security.actor.username },
    { id: "gateways", label: "Passerelles de sécurité", ok: security.gateways.control && security.gateways.readonly, required: true, detail: "Lecture et actions privilégiées" },
    { id: "system", label: "Intégration YunoHost", ok: system.platform.yunohost, required: true, detail: `${system.platform.hostname} · YunoHost ${system.platform.versions.yunohost} · ${system.health === "healthy" ? "sain" : "à diagnostiquer"}` },
    { id: "provider", label: "Moteur d’intelligence", ok: connected.length > 0, required: false, detail: connected.length ? `${connected.length} fournisseur(s) disponible(s)` : "À connecter dans Paramètres" },
  ];
}

export function requiredChecksPass(checks: ArcenalOnboardingCheck[]): boolean {
  return checks.filter((check) => check.required).every((check) => check.ok);
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
