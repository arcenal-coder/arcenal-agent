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

export interface DocumentTemplateFields {
  activity?: string;
  changeType?: "Création" | "Révision";
  number?: string;
  reason?: string;
  reference?: string;
  revision?: string;
  type?: string;
  validationDate?: string;
}

export function createDocumentTemplate(title: string, path: string, fields: DocumentTemplateFields = {}): string {
  const fallbackReference = path.split("/").at(-1)?.replace(/\.md$/i, "").toUpperCase() ?? "DOC";
  const reference = fields.reference?.trim() || fallbackReference;
  const revision = fields.revision?.trim() || "1";
  return `---
reference: ${reference}
titre: ${title}
type: ${fields.type?.trim() || "Note"}
activite: ${fields.activity?.trim() || ""}
numerotation: ${fields.number?.trim() || reference}
nature: ${fields.changeType || "Création"}
date_validation: ${fields.validationDate?.trim() || ""}
revision: ${revision}
motif: ${fields.reason?.trim() || ""}
version: ${revision}
statut: Brouillon
proprietaire: ""
date_application: ${fields.validationDate?.trim() || ""}
prochaine_revue: ""
perimetre: ${fields.activity?.trim() || "ARCenal"}
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
  return [document.title, document.reference, document.type, document.activity, document.number, document.change_type, document.reason, document.owner, ...document.tags]
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
  const header = ["Dénomination", "Activité", "Numérotation", "Titre", "Création ou révision", "Date de validation", "Révision N°", "Motif", "Statut"];
  const rows = documents.map((document) => [document.type, document.activity, document.number, document.title, document.change_type, document.validation_date, document.revision, document.reason, document.status]);
  return [header, ...rows].map((row) => row.map(escapeCsvCell).join(";")).join("\n");
}

export function withDocumentStatus(content: string, status: ArcenalDocumentStatus): string {
  if (!content.startsWith("---")) return `---\nstatut: ${status}\n---\n${content}`;
  if (/^statut\s*:/m.test(content)) return content.replace(/^statut\s*:.*$/m, `statut: ${status}`);
  return content.replace(/^---\s*\n/, `---\nstatut: ${status}\n`);
}

function escapeCsvCell(value: string): string {
  const protectedValue = /^[\s]*[=+\-@]/.test(value) ? `'${value}` : value;
  return `"${protectedValue.replaceAll('"', '""')}"`;
}
