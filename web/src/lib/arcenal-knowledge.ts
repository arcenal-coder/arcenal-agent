import type { ArcenalDocumentSummary, ArcenalDocumentStatus } from "@/lib/api";

export function slugifyDocumentTitle(title: string): string {
  return title
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

export function createDocumentTemplate(title: string, path: string): string {
  const reference = path.split("/").at(-1)?.replace(/\.md$/i, "").toUpperCase() ?? "DOC";
  return `---
reference: ${reference}
titre: ${title}
type: Note
version: 1
statut: Brouillon
proprietaire: ""
date_application: ""
prochaine_revue: ""
perimetre: ARCenal
tags: []
---
# ${title}

Commencez la rédaction ici.
`;
}

export function filterDocuments(
  documents: readonly ArcenalDocumentSummary[],
  query: string,
): ArcenalDocumentSummary[] {
  const needle = query.trim().toLocaleLowerCase("fr");
  if (!needle) return [...documents];
  return documents.filter((document) => documentSearchText(document).includes(needle));
}

function documentSearchText(document: ArcenalDocumentSummary): string {
  return [document.title, document.reference, document.type, document.owner, ...document.tags]
    .join(" ")
    .toLocaleLowerCase("fr");
}

export function statusTone(status: ArcenalDocumentStatus): string {
  const tones: Record<ArcenalDocumentStatus, string> = {
    "Brouillon": "draft",
    "En révision": "review",
    "À approuver": "approval",
    "Applicable": "applicable",
    "Archivé": "archived",
  };
  return tones[status];
}

export function ldaToCsv(documents: readonly ArcenalDocumentSummary[]): string {
  const header = ["Référence", "Titre", "Type", "Version", "Propriétaire", "Date d’application", "Prochaine revue", "Périmètre"];
  const rows = documents.map((document) => [document.reference, document.title, document.type, document.version, document.owner, document.application_date, document.review_date, document.scope]);
  return [header, ...rows].map((row) => row.map(escapeCsvCell).join(";")).join("\n");
}

function escapeCsvCell(value: string): string {
  const protectedValue = /^[\s]*[=+\-@]/.test(value) ? `'${value}` : value;
  return `"${protectedValue.replaceAll('"', '""')}"`;
}
