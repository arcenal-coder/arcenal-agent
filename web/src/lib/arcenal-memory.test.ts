import { describe, expect, it } from "vitest";
import { isArcenalMemoryEntriesResponse } from "./arcenal-memory";

describe("contrat de la mémoire ARC", () => {
  it("accepte un catalogue structuré", () => {
    expect(isArcenalMemoryEntriesResponse({ entries: [{ id: "1", title: "Décision", content: "Texte" }] })).toBe(true);
  });

  it("accepte un catalogue vide", () => {
    expect(isArcenalMemoryEntriesResponse({ entries: [] })).toBe(true);
  });

  it("refuse une réponse incomplète ou mal typée", () => {
    expect(isArcenalMemoryEntriesResponse({})).toBe(false);
    expect(isArcenalMemoryEntriesResponse({ entries: [{ id: 1, title: "Décision" }] })).toBe(false);
    expect(isArcenalMemoryEntriesResponse(null)).toBe(false);
  });
});
