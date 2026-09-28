export const ARCENAL_SETTINGS_TABS = [
  { id: "appearance", label: "Apparence" },
  { id: "providers", label: "Fournisseurs IA" },
  { id: "access", label: "Accès" },
  { id: "security", label: "Sécurité" },
] as const;

export type ArcenalSettingsTab = (typeof ARCENAL_SETTINGS_TABS)[number]["id"];

export function isArcenalSettingsTab(value: string): value is ArcenalSettingsTab {
  return ARCENAL_SETTINGS_TABS.some((tab) => tab.id === value);
}
