import { describe, expect, it } from "vitest";
import { ARCENAL_SETTINGS_TABS, isArcenalSettingsTab } from "./arcenal-settings-tabs";

describe("navigation des paramètres ARC", () => {
  it("expose chaque section implémentée une seule fois", () => {
    const ids = ARCENAL_SETTINGS_TABS.map((tab) => tab.id);

    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toEqual(["general", "appearance", "providers", "frugal", "access", "tools", "system", "security", "backups"]);
    expect(ids).not.toEqual(expect.arrayContaining(["context", "memory", "directives"]));
  });

  it("refuse un onglet inconnu", () => {
    expect(isArcenalSettingsTab("providers")).toBe(true);
    expect(isArcenalSettingsTab("terminal")).toBe(false);
    expect(isArcenalSettingsTab("")).toBe(false);
  });
});
