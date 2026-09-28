import type { ArcenalProviderProbe, ArcenalProviderStatusesResponse } from "@/lib/api";

const CONNECTION_STATES = new Set(["connected", "invalid", "missing", "unreachable"]);

export function isProviderStatusesResponse(value: unknown): value is ArcenalProviderStatusesResponse {
  if (!isRecord(value) || !isRecord(value.providers)) return false;
  return Object.values(value.providers).every(isProviderProbe);
}

function isProviderProbe(value: unknown): value is ArcenalProviderProbe {
  if (!isRecord(value) || !Array.isArray(value.models)) return false;
  const texts = [value.message, value.provider, value.tested_at, ...value.models];
  return typeof value.configured === "boolean" && CONNECTION_STATES.has(value.connection as string) && texts.every((item) => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
