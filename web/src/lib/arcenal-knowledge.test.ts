import { describe, expect, it } from "vitest";
import type { ArcenalDocumentSummary } from "@/lib/api";
import { createDocumentTemplate, filterDocuments, ldaToCsv, slugifyDocumentTitle, statusTone } from "@/lib/arcenal-knowledge";

const DOCUMENT: ArcenalDocumentSummary = {
  application_date: "2026-09-22",
  backlinks: [],
  excerpt: "Maîtrise des documents",
  history_count: 0,
  links: [],
  owner: "Direction Q&D",
  path: "QSSERP/PR-QSSE-001.md",
  reference: "PR-QSSE-001",
  review_date: "2027-09-22",
  scope: "ONYX",
  status: "Applicable",
  tags: ["qualité", "documentation"],
  title: "Gestion documentaire",
  type: "Procédure",
  updated_at: "2026-09-22T10:00:00Z",
  version: "4",
};

describe("modèle documentaire ARCenal", () => {
  it("normalise un titre accentué en chemin portable", () => {
    expect(slugifyDocumentTitle("Évaluation & maîtrise QSSÉ")).toBe("evaluation-maitrise-qsse");
  });

  it("construit un brouillon Markdown avec ses métadonnées", () => {
    const content = createDocumentTemplate("Gestion documentaire", DOCUMENT.path);
    expect(content).toContain("reference: PR-QSSE-001");
    expect(content).toContain("statut: Brouillon");
    expect(content).toContain("# Gestion documentaire");
  });

  it("filtre par référence, propriétaire et tag", () => {
    expect(filterDocuments([DOCUMENT], "qsse-001")).toEqual([DOCUMENT]);
    expect(filterDocuments([DOCUMENT], "direction q&d")).toEqual([DOCUMENT]);
    expect(filterDocuments([DOCUMENT], "qualité")).toEqual([DOCUMENT]);
  });

  it("renvoie tous les documents pour une recherche vide", () => {
    expect(filterDocuments([DOCUMENT], "   ")).toEqual([DOCUMENT]);
  });

  it("associe un ton stable à chaque statut autorisé", () => {
    expect(statusTone("Applicable")).toBe("applicable");
    expect(statusTone("À approuver")).toBe("approval");
  });

  it("exporte la LDA en CSV français sans casser les guillemets", () => {
    const csv = ldaToCsv([{ ...DOCUMENT, title: 'Gestion "maîtrisée"' }]);
    expect(csv).toContain('"PR-QSSE-001";"Gestion ""maîtrisée"""');
    expect(csv.split("\n")).toHaveLength(2);
  });

  it("neutralise une formule injectée dans un export CSV", () => {
    const csv = ldaToCsv([{ ...DOCUMENT, owner: "=HYPERLINK(\"https://invalid\")" }]);
    expect(csv).toContain("'=HYPERLINK");
  });
});
