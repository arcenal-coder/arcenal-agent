import type { ArcenalMemoryEntriesResponse, ArcenalMemoryEntry } from "@/lib/api";

export function isArcenalMemoryEntriesResponse(value: unknown): value is ArcenalMemoryEntriesResponse {
  if (!isRecord(value) || !Array.isArray(value.entries)) return false;
  return value.entries.every(isMemoryEntry);
}

function isMemoryEntry(value: unknown): value is ArcenalMemoryEntry {
  if (!isRecord(value)) return false;
  return [value.id, value.title, value.content].every((field) => typeof field === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
