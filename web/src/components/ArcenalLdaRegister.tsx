import { useMemo, useState, type ReactElement } from "react";
import { Archive, ChevronLeft, ChevronRight, Download, FileText, Filter, Plus, Search } from "lucide-react";
import type { ArcenalDocumentSummary } from "@/lib/api";
import { filterLdaDocuments, paginateLdaDocuments, uniqueLdaValues, type LdaRegisterTab } from "@/lib/arcenal-lda";
import { ldaToCsv } from "@/lib/arcenal-knowledge";

interface ArcenalLdaRegisterProps {
  busy: boolean;
  documents: readonly ArcenalDocumentSummary[];
  onArchive: (document: ArcenalDocumentSummary) => Promise<void>;
  onCreate: () => void;
  onOpen: (path: string) => void;
}

export function ArcenalLdaRegister(props: ArcenalLdaRegisterProps): ReactElement {
  const [tab, setTab] = useState<LdaRegisterTab>("usable");
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [activity, setActivity] = useState("");
  const [page, setPage] = useState(1);
  const filtered = useMemo(() => filterLdaDocuments(props.documents, { activity, query, tab, type }), [activity, props.documents, query, tab, type]);
  const pagination = paginateLdaDocuments(filtered, page);
  const changeTab = (value: LdaRegisterTab): void => { setTab(value); setPage(1); };
  return <section className="arc-lda-register" aria-busy={props.busy}>
    <RegisterHeading onCreate={props.onCreate} />
    <RegisterTabs documents={props.documents} tab={tab} onChange={changeTab} />
    <RegisterToolbar documents={props.documents} filtered={filtered} query={query} type={type} activity={activity} onQuery={setQuery} onType={setType} onActivity={setActivity} />
    <RegisterTable documents={pagination.documents} archived={tab === "archived"} onArchive={props.onArchive} onOpen={props.onOpen} />
    <RegisterPagination page={pagination.page} pages={pagination.pages} total={pagination.total} onPage={setPage} />
  </section>;
}

function RegisterHeading({ onCreate }: { onCreate: () => void }): ReactElement {
  return <header className="arc-lda-heading"><div><span>Registre maîtrisé · QSSERP</span><h2>Liste des documents applicables</h2></div><em>FORM S 01</em><button type="button" className="arc-primary-button" onClick={onCreate}><Plus aria-hidden /> Ajouter un document</button></header>;
}

function RegisterTabs({ documents, tab, onChange }: { documents: readonly ArcenalDocumentSummary[]; tab: LdaRegisterTab; onChange: (tab: LdaRegisterTab) => void }): ReactElement {
  const usable = documents.filter((document) => document.status === "Applicable").length;
  const archived = documents.filter((document) => document.status === "Archivé").length;
  return <div className="arc-lda-tabs"><button type="button" aria-pressed={tab === "usable"} onClick={() => onChange("usable")}><strong>{usable}</strong><span>Utilisables</span></button><button type="button" aria-pressed={tab === "archived"} onClick={() => onChange("archived")}><strong>{archived}</strong><span>Archivés</span></button></div>;
}

interface ToolbarProps {
  activity: string;
  documents: readonly ArcenalDocumentSummary[];
  filtered: readonly ArcenalDocumentSummary[];
  onActivity: (value: string) => void;
  onQuery: (value: string) => void;
  onType: (value: string) => void;
  query: string;
  type: string;
}

function RegisterToolbar(props: ToolbarProps): ReactElement {
  return <div className="arc-lda-toolbar"><strong>{props.filtered.length} résultat{props.filtered.length > 1 ? "s" : ""}</strong><div><label><Search aria-hidden /><input aria-label="Rechercher dans la LDA" value={props.query} onChange={(event) => props.onQuery(event.target.value)} placeholder="Rechercher…" /></label><FilterSelect label="Activité" value={props.activity} values={uniqueLdaValues(props.documents, "activity")} onChange={props.onActivity} /><FilterSelect label="Dénomination" value={props.type} values={uniqueLdaValues(props.documents, "type")} onChange={props.onType} /><button type="button" className="arc-icon-button" onClick={() => downloadCsv(props.filtered)} title="Exporter la sélection"><Download aria-hidden /></button></div></div>;
}

function FilterSelect({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }): ReactElement {
  return <label className="arc-lda-filter"><Filter aria-hidden /><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}><option value="">{label}</option>{values.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>;
}

function downloadCsv(documents: readonly ArcenalDocumentSummary[]): void {
  const blob = new Blob(["\ufeff", ldaToCsv(documents)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: "LDA-ARCenal.csv" });
  link.click();
  URL.revokeObjectURL(url);
}

interface RegisterTableProps {
  archived: boolean;
  documents: readonly ArcenalDocumentSummary[];
  onArchive: (document: ArcenalDocumentSummary) => Promise<void>;
  onOpen: (path: string) => void;
}

function RegisterTable(props: RegisterTableProps): ReactElement {
  return <div className="arc-lda-table-wrap"><table className="arc-lda-table"><thead><tr><th>Dénomination</th><th>Activité</th><th>Numérotation</th><th>Titre</th><th>Création ou révision</th><th>Date de validation</th><th>Rév. N°</th><th>Motif</th><th>Fiche document</th>{!props.archived && <th>Archiver</th>}</tr></thead><tbody>{props.documents.map((document) => <RegisterRow key={document.path} document={document} archived={props.archived} onArchive={props.onArchive} onOpen={props.onOpen} />)}</tbody></table>{props.documents.length === 0 && <div className="arc-lda-empty"><FileText aria-hidden /><p>Aucun document ne correspond à cette vue.</p></div>}</div>;
}

function RegisterRow({ document, archived, onArchive, onOpen }: { document: ArcenalDocumentSummary; archived: boolean; onArchive: (document: ArcenalDocumentSummary) => Promise<void>; onOpen: (path: string) => void }): ReactElement {
  const requestArchive = (): void => {
    if (!window.confirm(`Archiver « ${document.title} » ?`)) return;
    void onArchive(document);
  };
  return <tr><td><Badge tone="green">{document.type}</Badge></td><td><Badge tone="blue">{document.activity || "Non définie"}</Badge></td><td>{document.number || document.reference}</td><td className="arc-lda-title">{document.title}</td><td><Badge tone="gold">{document.change_type || "Création"}</Badge></td><td>{document.validation_date || "—"}</td><td>{document.revision || document.version}</td><td>{document.reason || "—"}</td><td><button type="button" className="arc-table-action" onClick={() => onOpen(document.path)} title="Ouvrir la fiche"><FileText aria-hidden /></button></td>{!archived && <td><button type="button" className="arc-table-action danger" onClick={requestArchive} title="Archiver le document"><Archive aria-hidden /></button></td>}</tr>;
}

function Badge({ children, tone }: { children: string; tone: "blue" | "gold" | "green" }): ReactElement {
  return <span className="arc-lda-badge" data-tone={tone}>{children}</span>;
}

function RegisterPagination({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (page: number) => void }): ReactElement {
  return <footer className="arc-lda-pagination"><span>20 lignes · {total} document{total > 1 ? "s" : ""}</span><button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Page précédente"><ChevronLeft aria-hidden /></button><strong>{page} / {pages}</strong><button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Page suivante"><ChevronRight aria-hidden /></button></footer>;
}
