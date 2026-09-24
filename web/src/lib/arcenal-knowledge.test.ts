import { describe, expect, it } from "vitest";
import type { ArcenalDocumentSummary } from "@/lib/api";
import { createDocumentTemplate, filterDocuments, ldaToCsv, slugifyDocumentTitle, statusTone, withDocumentStatus } from "@/lib/arcenal-knowledge";

const DOCUMENT: ArcenalDocumentSummary = {
  activity: "Qualité",
  application_date: "2026-09-22",
  backlinks: [],
  change_type: "Révision",
  excerpt: "Maîtrise des documents",
  history_count: 0,
  links: [],
  number: "1",
  owner: "Direction Q&D",
  path: "QSSERP/PR-QSSE-001.md",
  reference: "PR-QSSE-001",
  reason: "Mise à jour du processus",
  revision: "4",
  review_date: "2027-09-22",
  scope: "ONYX",
  status: "Applicable",
  tags: ["qualité", "documentation"],
  title: "Gestion documentaire",
  type: "Procédure",
  updated_at: "2026-09-22T10:00:00Z",
  validation_date: "2026-09-22",
  version: "4",
};

describe("modèle documentaire ARCenal", () => {
  it("normalise un titre accentué en chemin portable", () => {
    expect(slugifyDocumentTitle("Évaluation & maîtrise QSSÉ")).toBe("evaluation-maitrise-qsse");
  });

  it("construit un brouillon Markdown avec ses métadonnées", () => {
    const content = createDocumentTemplate("Gestion documentaire", DOCUMENT.path, {
      activity: "Qualité",
      changeType: "Révision",
      number: "1",
      revision: "4",
      validationDate: "2026-09-22",
    });
    expect(content).toContain("reference: PR-QSSE-001");
    expect(content).toContain("activite: Qualité");
    expect(content).toContain("nature: Révision");
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
    expect(csv).toContain('"Procédure";"Qualité";"1";"Gestion ""maîtrisée"""');
    expect(csv.split("\n")).toHaveLength(2);
  });

  it("neutralise une formule injectée dans un export CSV", () => {
    const csv = ldaToCsv([{ ...DOCUMENT, reason: "=HYPERLINK(\"https://invalid\")" }]);
    expect(csv).toContain("'=HYPERLINK");
  });

  it("archive un document qui possède déjà un statut", () => {
    expect(withDocumentStatus("---\nstatut: Applicable\n---\n# Note", "Archivé"))
      .toContain("statut: Archivé");
  });

  it("ajoute un en-tête documentaire au contenu sans métadonnées", () => {
    expect(withDocumentStatus("# Note", "Applicable"))
      .toBe("---\nstatut: Applicable\n---\n# Note");
  });
});
