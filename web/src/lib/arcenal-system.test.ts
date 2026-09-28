import { describe, expect, it } from "vitest";
import { isArcenalSystemInventory, systemRecordDetail, systemRecordLabel } from "./arcenal-system";

const collection = { error: "", items: [] };

describe("inventaire système ARCenal", () => {
  it("valide une réponse YunoHost complète", () => {
    const inventory = { applications: collection, backups: collection, certificates: [], diagnostics: collection, domains: collection, errors: [], updates: collection, users: collection };
    expect(isArcenalSystemInventory(inventory)).toBe(true);
  });

  it("refuse une collection externe mal formée", () => {
    const inventory = { applications: { error: 500, items: [] }, backups: collection, certificates: [], diagnostics: collection, domains: collection, errors: [], updates: collection, users: collection };
    expect(isArcenalSystemInventory(inventory)).toBe(false);
  });

  it("présente les champs connus sans dépendre du format exact YunoHost", () => {
    expect(systemRecordLabel({ id: "nextcloud", name: "Nextcloud" })).toBe("Nextcloud");
    expect(systemRecordDetail({ status: "up-to-date", version: "30.0" })).toBe("30.0");
  });
});
