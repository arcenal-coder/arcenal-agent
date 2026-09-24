import type { ArcenalDocumentSummary } from "@/lib/api";
import { filterDocuments } from "@/lib/arcenal-knowledge";

export type LdaRegisterTab = "usable" | "pending" | "archived";

export interface LdaFilters {
  activity: string;
  query: string;
  tab: LdaRegisterTab;
  type: string;
}

export interface LdaPage {
  documents: ArcenalDocumentSummary[];
  page: number;
  pages: number;
  total: number;
}

export function filterLdaDocuments(
  documents: readonly ArcenalDocumentSummary[],
  filters: LdaFilters,
): ArcenalDocumentSummary[] {
  const statuses = statusesForTab(filters.tab);
  return filterDocuments([...documents], filters.query).filter((document) => (
    statuses.has(document.status)
    && matches(document.activity, filters.activity)
    && matches(document.type, filters.type)
  ));
}

function statusesForTab(tab: LdaRegisterTab): ReadonlySet<string> {
  if (tab === "usable") return new Set(["Applicable"]);
  if (tab === "archived") return new Set(["Archivé"]);
  return new Set(["Brouillon", "En révision", "À approuver"]);
}

export function uniqueLdaValues(
  documents: readonly ArcenalDocumentSummary[],
  field: "activity" | "type",
): string[] {
  return [...new Set(documents.map((document) => document[field]).filter(Boolean))]
    .sort((left, right) => left.localeCompare(right, "fr"));
}

export function paginateLdaDocuments(
  documents: readonly ArcenalDocumentSummary[],
  requestedPage: number,
  pageSize = 20,
): LdaPage {
  const pages = Math.max(1, Math.ceil(documents.length / pageSize));
  const page = Math.min(Math.max(1, requestedPage), pages);
  const start = (page - 1) * pageSize;
  return { documents: documents.slice(start, start + pageSize), page, pages, total: documents.length };
}

function matches(value: string, expected: string): boolean {
  return !expected || value === expected;
}
