import type { ArcenalSystemCollection, ArcenalSystemInventory } from "./api";

export function isArcenalSystemInventory(value: unknown): value is ArcenalSystemInventory {
  const root = record(value);
  const collections = [root.applications, root.backups, root.diagnostics, root.domains, root.updates, root.users];
  return collections.every(isCollection) && Array.isArray(root.certificates) && stringArray(root.errors);
}

export function systemRecordLabel(item: Record<string, unknown>): string {
  return text(item.label, item.name, item.domain, item.id, item.username, item.filename) || "Élément YunoHost";
}

export function systemRecordDetail(item: Record<string, unknown>): string {
  return text(item.version, item.status, item.state, item.path, item.mail, item.created_at) || "Détail non communiqué";
}

function isCollection(value: unknown): value is ArcenalSystemCollection {
  const candidate = record(value);
  return typeof candidate.error === "string" && Array.isArray(candidate.items) && candidate.items.every(isRecord);
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function record(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function text(...values: unknown[]): string {
  const value = values.find((item) => typeof item === "string" && item.trim());
  return typeof value === "string" ? value : "";
}
