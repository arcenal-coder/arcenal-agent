export const ARCENAL_SETTINGS_TABS = [
  { id: "general", label: "Général" },
  { id: "appearance", label: "Apparence" },
  { id: "context", label: "Contexte" },
  { id: "directives", label: "Directives" },
  { id: "providers", label: "Fournisseurs IA" },
  { id: "access", label: "Accès" },
  { id: "security", label: "Sécurité" },
] as const;

export type ArcenalSettingsTab = (typeof ARCENAL_SETTINGS_TABS)[number]["id"];

export function isArcenalSettingsTab(value: string): value is ArcenalSettingsTab {
  return ARCENAL_SETTINGS_TABS.some((tab) => tab.id === value);
}
