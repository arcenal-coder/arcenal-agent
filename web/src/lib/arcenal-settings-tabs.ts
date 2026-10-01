export const ARCENAL_SETTINGS_TABS = [
  { id: "general", label: "Général" },
  { id: "appearance", label: "Apparence" },
  { id: "context", label: "Contexte" },
  { id: "memory", label: "Mémoire" },
  { id: "directives", label: "Directives" },
  { id: "providers", label: "Fournisseurs IA" },
  { id: "frugal", label: "IA & consommation" },
  { id: "automations", label: "Automatisations" },
  { id: "access", label: "Accès" },
  { id: "tools", label: "Outils" },
  { id: "system", label: "Système" },
  { id: "security", label: "Sécurité" },
  { id: "backups", label: "Sauvegardes" },
] as const;

export type ArcenalSettingsTab = (typeof ARCENAL_SETTINGS_TABS)[number]["id"];

export function isArcenalSettingsTab(value: string): value is ArcenalSettingsTab {
  return ARCENAL_SETTINGS_TABS.some((tab) => tab.id === value);
}
