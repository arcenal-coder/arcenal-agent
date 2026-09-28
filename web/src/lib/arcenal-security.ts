import type { ArcenalSecurityAction, ArcenalSecurityOverview } from "./api";

export function isArcenalSecurityOverview(value: unknown): value is ArcenalSecurityOverview {
  const root = record(value);
  const actor = record(root.actor);
  const gateways = record(root.gateways);
  const audit = record(root.audit);
  return typeof actor.username === "string"
    && stringArray(actor.roles)
    && booleanGateways(gateways)
    && Array.isArray(root.actions)
    && root.actions.every(isAction)
    && Array.isArray(root.approvals)
    && Array.isArray(audit.events)
    && typeof audit.integrity === "boolean";
}

export function authorizationLabel(value: number): string {
  if (value >= 3) return "Confirmation obligatoire";
  if (value === 2) return "Action encadrée";
  return "Lecture seule";
}

export function riskLabel(value: ArcenalSecurityAction["risk"]): string {
  return { none: "Aucun", low: "Faible", medium: "Modéré", high: "Élevé" }[value];
}

function isAction(value: unknown): value is ArcenalSecurityAction {
  const action = record(value);
  return typeof action.id === "string"
    && typeof action.authorization === "number"
    && typeof action.description === "string"
    && typeof action.consequence === "string"
    && typeof action.rollback === "string"
    && stringArray(action.allowed_targets)
    && ["none", "low", "medium", "high"].includes(String(action.risk));
}

function booleanGateways(value: Record<string, unknown>): boolean {
  return typeof value.control === "boolean" && typeof value.readonly === "boolean";
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
