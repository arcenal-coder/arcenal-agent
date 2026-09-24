import { describe, expect, it } from "vitest";
import type { ArcenalDocumentSummary } from "@/lib/api";
import { filterLdaDocuments, paginateLdaDocuments, uniqueLdaValues } from "@/lib/arcenal-lda";

function document(overrides: Partial<ArcenalDocumentSummary> = {}): ArcenalDocumentSummary {
  return {
    activity: "Qualité",
    application_date: "",
    attachment_name: "",
    attachment_path: "",
    attachment_size: 0,
    backlinks: [],
    change_type: "Création",
    excerpt: "",
    history_count: 0,
    links: [],
    number: "1",
    owner: "",
    path: "QSSERP/document.md",
    reason: "",
    reference: "PRO-Q-01",
    revision: "1",
    review_date: "",
    scope: "ARCenal",
    status: "Applicable",
    tags: [],
    title: "Maîtrise documentaire",
    type: "Procédure",
    updated_at: "2026-09-24T10:00:00Z",
    validation_date: "2026-09-24",
    version: "1",
    ...overrides,
  };
}

describe("registre LDA", () => {
  it("affiche les documents applicables correspondant aux filtres", () => {
    const result = filterLdaDocuments([document(), document({ status: "Archivé" })], {
      activity: "Qualité", query: "maîtrise", tab: "usable", type: "Procédure",
    });
    expect(result).toHaveLength(1);
  });

  it("sépare les archives et extrait les valeurs de filtre", () => {
    const documents = [document(), document({ activity: "Sécurité", status: "Archivé" })];
    expect(filterLdaDocuments(documents, { activity: "", query: "", tab: "archived", type: "" }))
      .toHaveLength(1);
    expect(uniqueLdaValues(documents, "activity")).toEqual(["Qualité", "Sécurité"]);
  });

  it("conserve les documents déposés dans la file à traiter", () => {
    const documents = [document({ status: "À approuver" }), document({ status: "Brouillon" })];
    expect(filterLdaDocuments(documents, { activity: "", query: "", tab: "pending", type: "" }))
      .toHaveLength(2);
  });

  it("borne la pagination quand la page demandée n'existe pas", () => {
    const result = paginateLdaDocuments([document(), document({ path: "deux.md" })], 99, 1);
    expect(result.page).toBe(2);
    expect(result.documents[0]?.path).toBe("deux.md");
  });

  it("retourne une première page vide pour une liste vide", () => {
    expect(paginateLdaDocuments([], 0)).toEqual({ documents: [], page: 1, pages: 1, total: 0 });
  });
});
