import { describe, expect, it } from "vitest";
import { backupArchiveNames } from "./arcenal-backups";

describe("archives de sauvegarde ARCenal", () => {
  it("retient les noms YunoHost utilisables", () => {
    expect(backupArchiveNames([{ id: "arcenal-manual" }, { name: "daily.2026-09-28" }])).toEqual(["arcenal-manual", "daily.2026-09-28"]);
  });

  it("élimine les doublons et les entrées vides", () => {
    expect(backupArchiveNames([{ id: "arcenal" }, { name: "arcenal" }, {}])).toEqual(["arcenal"]);
  });

  it("refuse une cible pouvant sortir du catalogue YunoHost", () => {
    expect(backupArchiveNames([{ id: "../../root" }, { id: "nom avec espace" }])).toEqual([]);
  });
});
