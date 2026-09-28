import type { ArcenalSystemOverview } from "./api";

export interface ArcenalGeneralSettings {
  agentName: string;
  language: string;
  notificationEmail: string;
  organizationName: string;
  timezone: string;
}

export interface ArcenalAppearanceSettings {
  accentColor: string;
  buttonColor: string;
  faviconUrl: string;
  linkColor: string;
  logoUrl: string;
  textColor: string;
}

export interface ArcenalBranding {
  faviconUrl: string;
  logoUrl: string;
  title: string;
}

interface AppearanceRoot {
  style: Pick<CSSStyleDeclaration, "setProperty">;
}

export const ARCENAL_BRANDING_EVENT = "arcenal-branding-change";

const DEFAULT_GENERAL: Readonly<ArcenalGeneralSettings> = {
  agentName: "ARC",
  language: "fr",
  notificationEmail: "",
  organizationName: "ARCenal",
  timezone: "Europe/Paris",
};

const DEFAULT_APPEARANCE: Readonly<ArcenalAppearanceSettings> = {
  accentColor: "#9F3434",
  buttonColor: "#D95A35",
  faviconUrl: "",
  linkColor: "#174D70",
  logoUrl: "",
  textColor: "#1D2733",
};

export function generalSettingsFromConfig(config: Record<string, unknown>): ArcenalGeneralSettings {
  const values = nestedRecord(config, "arcenal", "general");
  return {
    agentName: stringValue(values.agent_name, DEFAULT_GENERAL.agentName),
    language: stringValue(values.language, DEFAULT_GENERAL.language),
    notificationEmail: stringValue(values.notification_email, ""),
    organizationName: stringValue(values.organization_name, DEFAULT_GENERAL.organizationName),
    timezone: stringValue(values.timezone, DEFAULT_GENERAL.timezone),
  };
}

export function appearanceSettingsFromConfig(config: Record<string, unknown>): ArcenalAppearanceSettings {
  const values = nestedRecord(config, "arcenal", "appearance");
  return {
    accentColor: colorValue(values.accent_color, DEFAULT_APPEARANCE.accentColor),
    buttonColor: colorValue(values.button_color, DEFAULT_APPEARANCE.buttonColor),
    faviconUrl: urlValue(values.favicon_url),
    linkColor: colorValue(values.link_color, DEFAULT_APPEARANCE.linkColor),
    logoUrl: urlValue(values.logo_url),
    textColor: colorValue(values.text_color, DEFAULT_APPEARANCE.textColor),
  };
}

export function generalSettingsConfig(settings: ArcenalGeneralSettings): Record<string, unknown> {
  return { arcenal: { general: {
    agent_name: settings.agentName.trim(), language: settings.language,
    notification_email: settings.notificationEmail.trim(),
    organization_name: settings.organizationName.trim(), timezone: settings.timezone,
  } } };
}

export function appearanceSettingsConfig(settings: ArcenalAppearanceSettings): Record<string, unknown> {
  return { arcenal: { appearance: {
    accent_color: settings.accentColor, button_color: settings.buttonColor,
    favicon_url: settings.faviconUrl.trim(), link_color: settings.linkColor,
    logo_url: settings.logoUrl.trim(), text_color: settings.textColor,
  } } };
}

export function isValidBrandUrl(value: string): boolean {
  if (!value.trim()) return true;
  if (/^\/(?:[A-Za-z0-9._~-]+\/)*api\/plugins\/arcenal-supervisor\/branding\/assets\/(?:logo|favicon)(?:\?v=\d+)?$/.test(value)) return true;
  try {
    const protocol = new URL(value).protocol;
    return protocol === "https:" || protocol === "http:";
  } catch {
    return false;
  }
}

export function isCssHexColor(value: string): boolean {
  return /^#[0-9a-f]{6}$/i.test(value);
}

export function isValidNotificationEmail(value: string): boolean {
  if (!value.trim()) return true;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function isArcenalSystemOverview(value: unknown): value is ArcenalSystemOverview {
  const root = recordValue(value);
  const platform = recordValue(root.platform);
  const versions = recordValue(platform.versions);
  return [platform.hostname, platform.domain, versions.arc, versions.hermes, versions.yunohost, versions.debian]
    .every((entry) => typeof entry === "string" && Boolean(entry));
}

export function applyAppearance(settings: ArcenalAppearanceSettings, root: AppearanceRoot): void {
  root.style.setProperty("--arc-wine", settings.accentColor);
  root.style.setProperty("--arc-action", settings.buttonColor);
  root.style.setProperty("--arc-link", settings.linkColor);
  root.style.setProperty("--arc-text", settings.textColor);
}

export function productBranding(config: Record<string, unknown>, fallback: ArcenalBranding): ArcenalBranding {
  const general = generalSettingsFromConfig(config);
  const appearance = appearanceSettingsFromConfig(config);
  return {
    faviconUrl: appearance.faviconUrl || fallback.faviconUrl,
    logoUrl: appearance.logoUrl || fallback.logoUrl,
    title: general.organizationName || fallback.title,
  };
}

function nestedRecord(source: Record<string, unknown>, first: string, second: string): Record<string, unknown> {
  const parent = recordValue(source[first]);
  return recordValue(parent[second]);
}

function recordValue(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function colorValue(value: unknown, fallback: string): string {
  return typeof value === "string" && isCssHexColor(value) ? value : fallback;
}

function urlValue(value: unknown): string {
  return typeof value === "string" && isValidBrandUrl(value) ? value : "";
}
