import type { ArcenalCapabilitiesResponse, ArcenalCapability, ArcenalCapabilityRisk, ArcenalCapabilityUsage, ToolsetInfo } from "./api";

export interface CapabilityView {
  confirmation: boolean;
  configured: boolean;
  description: string;
  enabled: boolean;
  id: string;
  lastUsage: ArcenalCapabilityUsage | null;
  mutable: boolean;
  name: string;
  origin: "arcenal" | "hermes";
  permission: string;
  risk: ArcenalCapabilityRisk;
  tools: string[];
}

const RISKS = new Set<ArcenalCapabilityRisk>(["high", "low", "medium", "none"]);
const STATUSES = new Set(["blocked", "error", "success", "unknown"]);
const HIGH_RISK_TOOLSETS = new Set(["code_execution", "computer_use", "project", "terminal"]);
const MEDIUM_RISK_TOOLSETS = new Set(["browser", "cronjob", "file", "mcp", "webhooks"]);

export function isCapabilitiesResponse(value: unknown): value is ArcenalCapabilitiesResponse {
  const root = recordValue(value);
  const usage = recordValue(root?.usage);
  if (!root || !Array.isArray(root.capabilities) || !usage) return false;
  return root.capabilities.every(isArcCapability) && Object.values(usage).every(isUsage);
}

export function capabilityViews(response: ArcenalCapabilitiesResponse, toolsets: ToolsetInfo[]): CapabilityView[] {
  const arc = response.capabilities.map(fromArcCapability);
  const inherited = toolsets.map((toolset) => fromHermesToolset(toolset, response.usage));
  return [...arc, ...inherited].sort((left, right) => left.name.localeCompare(right.name, "fr"));
}

function fromArcCapability(capability: ArcenalCapability): CapabilityView {
  const { last_usage: lastUsage, ...metadata } = capability;
  return { ...metadata, configured: true, id: capability.name, lastUsage, tools: [capability.name] };
}

function fromHermesToolset(toolset: ToolsetInfo, usage: Record<string, ArcenalCapabilityUsage>): CapabilityView {
  const risk = inheritedRisk(toolset.name);
  return {
    confirmation: risk === "high",
    configured: toolset.configured,
    description: toolset.description || `Capacité technique héritée du moteur Hermes (${toolset.platform_label}).`,
    enabled: toolset.enabled,
    id: toolset.name,
    lastUsage: latestUsage(toolset.tools, usage),
    mutable: true,
    name: toolset.label.trim() || toolset.name,
    origin: "hermes",
    permission: toolset.platform_label || "Moteur Hermes",
    risk,
    tools: toolset.tools,
  };
}

function inheritedRisk(name: string): ArcenalCapabilityRisk {
  if (HIGH_RISK_TOOLSETS.has(name)) return "high";
  if (MEDIUM_RISK_TOOLSETS.has(name)) return "medium";
  return "low";
}

function latestUsage(names: string[], usage: Record<string, ArcenalCapabilityUsage>): ArcenalCapabilityUsage | null {
  const records = names.map((name) => usage[name]).filter((item): item is ArcenalCapabilityUsage => Boolean(item));
  return records.sort((left, right) => right.last_used.localeCompare(left.last_used))[0] ?? null;
}

function isArcCapability(value: unknown): value is ArcenalCapability {
  const item = recordValue(value);
  if (!item || item.origin !== "arcenal" || typeof item.confirmation !== "boolean") return false;
  if (typeof item.enabled !== "boolean" || typeof item.mutable !== "boolean") return false;
  if (![item.description, item.name, item.permission].every(isText) || !RISKS.has(item.risk as ArcenalCapabilityRisk)) return false;
  return item.last_usage === null || isUsage(item.last_usage);
}

function isUsage(value: unknown): value is ArcenalCapabilityUsage {
  const item = recordValue(value);
  if (!item || !Number.isInteger(item.count) || !Number.isInteger(item.duration_ms)) return false;
  return isText(item.last_used) && STATUSES.has(String(item.last_status));
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}
