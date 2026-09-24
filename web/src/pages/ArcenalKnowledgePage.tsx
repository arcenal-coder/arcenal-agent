import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactElement } from "react";
import { Link } from "react-router";
import { BookOpen, Check, CircleAlert, FilePenLine, Files, GitFork, Library, Paperclip, Plus, Save, Search, X } from "lucide-react";
import { ArcenalLdaRegister } from "@/components/ArcenalLdaRegister";
import { Markdown } from "@/components/Markdown";
import { api, type ArcenalDocumentSummary, type ArcenalKnowledgeOverview } from "@/lib/api";
import { createDocumentTemplate, filterDocuments, LDA_ATTACHMENT_ACCEPT, slugifyDocumentTitle, statusTone, validateLdaAttachment, withDocumentStatus, type DocumentTemplateFields } from "@/lib/arcenal-knowledge";

type KnowledgeMode = "vault" | "lda" | "wiki";
type EditorMode = "read" | "edit";

export default function ArcenalKnowledgePage(): ReactElement {
  const [overview, setOverview] = useState<ArcenalKnowledgeOverview | null>(null);
  const [selectedPath, setSelectedPath] = useState("");
  const [content, setContent] = useState("");
  const [query, setQuery] = useState("");
  const [searchPaths, setSearchPaths] = useState<string[] | null>(null);
  const [mode, setMode] = useState<KnowledgeMode>("vault");
  const [editorMode, setEditorMode] = useState<EditorMode>("read");
  const [newDocumentOpen, setNewDocumentOpen] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  const loadOverview = useCallback(async (): Promise<void> => {
    try {
      const result = await api.getArcenalKnowledge();
      setOverview(result);
      setSelectedPath((current) => current || result.documents[0]?.path || "");
      setError("");
    } catch (cause) {
      setError(errorMessage(cause, "Chargement du coffre impossible."));
    } finally {
      setBusy(false);
    }
  }, []);
  const documents = useMemo(() => documentsForMode(overview, mode), [overview, mode]);
  const activePath = documents.some((document) => document.path === selectedPath)
    ? selectedPath
    : documents[0]?.path ?? "";

  useEffect(() => { void loadOverview(); }, [loadOverview]);
  useEffect(() => {
    if (!activePath) return;
    let cancelled = false;
    void api.getArcenalDocument(activePath)
      .then((result) => {
        if (!cancelled) setContent(result.content);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(errorMessage(cause, "Lecture du document impossible."));
    });
    return () => { cancelled = true; };
  }, [activePath]);
  useEffect(() => {
    const cleaned = query.trim();
    if (cleaned.length < 2) return;
    let cancelled = false;
    const timeout = window.setTimeout(() => {
      api.searchArcenalKnowledge(cleaned, 30)
        .then((result) => { if (!cancelled) setSearchPaths(result.results.map((item) => item.path)); })
        .catch((cause: unknown) => { if (!cancelled) setError(errorMessage(cause, "Recherche impossible.")); });
    }, 220);
    return () => { cancelled = true; window.clearTimeout(timeout); };
  }, [query]);

  const filtered = useMemo(() => filterVisibleDocuments(documents, query, searchPaths), [documents, query, searchPaths]);
  const selected = documents.find((item) => item.path === activePath) ?? null;
  const changeQuery = (value: string): void => {
    setQuery(value);
    setSearchPaths(null);
  };

  const save = async (): Promise<void> => {
    if (!activePath) return;
    try {
      await api.saveArcenalDocument(activePath, content);
      await loadOverview();
      setEditorMode("read");
    } catch (cause) {
      setError(errorMessage(cause, "Enregistrement impossible."));
    }
  };

  const archive = async (document: ArcenalDocumentSummary): Promise<void> => {
    try {
      const result = await api.getArcenalDocument(document.path);
      await api.saveArcenalDocument(document.path, withDocumentStatus(result.content, "Archivé"));
      await loadOverview();
    } catch (cause) {
      setError(errorMessage(cause, "Archivage impossible."));
    }
  };

  const openFromLda = (path: string): void => {
    setSelectedPath(path);
    setMode("vault");
  };

  return (
    <main className="arc-knowledge" aria-labelledby="knowledge-title">
      <KnowledgeHeader overview={overview} mode={mode} onModeChange={setMode} onCreate={() => setNewDocumentOpen(true)} />
      {error && <p className="arc-alert arc-alert-error" role="alert">{error}</p>}
      {mode === "lda" ? <ArcenalLdaRegister busy={busy} documents={overview?.documents ?? []} onArchive={archive} onCreate={() => setNewDocumentOpen(true)} onOpen={openFromLda} /> : <section className="arc-vault" aria-busy={busy}>
        <DocumentRail documents={filtered} selectedPath={activePath} query={query} mode={mode} onQuery={changeQuery} onSelect={setSelectedPath} />
        <DocumentCanvas document={selected} content={content} editorMode={editorMode} onContent={setContent} onMode={setEditorMode} onSave={() => void save()} />
        <KnowledgeContext document={selected} overview={overview} mode={mode} />
      </section>}
      {newDocumentOpen && <NewDocumentDialog onClose={() => setNewDocumentOpen(false)} onCreated={async (path, attached) => { setNewDocumentOpen(false); await loadOverview(); setSelectedPath(path); setMode("vault"); setEditorMode(attached ? "read" : "edit"); }} />}
    </main>
  );
}

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

function documentsForMode(overview: ArcenalKnowledgeOverview | null, mode: KnowledgeMode): ArcenalDocumentSummary[] {
  if (!overview) return [];
  if (mode === "lda") return overview.lda;
  if (mode === "wiki") return overview.wiki;
  return overview.documents;
}

function filterVisibleDocuments(documents: ArcenalDocumentSummary[], query: string, searchPaths: string[] | null): ArcenalDocumentSummary[] {
  if (!query.trim()) return documents;
  if (searchPaths === null) return filterDocuments(documents, query);
  const paths = new Set(searchPaths);
  return documents.filter((document) => paths.has(document.path));
}

function KnowledgeHeader({ overview, mode, onModeChange, onCreate }: { overview: ArcenalKnowledgeOverview | null; mode: KnowledgeMode; onModeChange: (mode: KnowledgeMode) => void; onCreate: () => void }): ReactElement {
  const stats = overview?.statistics;
  return <header className="arc-knowledge-header"><div><p>Volet 3 · Intelligence documentaire</p><h1 id="knowledge-title">RAG, LDA et wiki</h1><span>Un coffre Markdown portable, relié et exploitable par ARC.</span></div><div className="arc-knowledge-actions"><div className="arc-mode-switch"><ModeButton active={mode === "vault"} label="Coffre" icon={Library} onClick={() => onModeChange("vault")} /><ModeButton active={mode === "lda"} label={`LDA · ${stats?.applicable ?? 0}`} icon={Files} onClick={() => onModeChange("lda")} /><ModeButton active={mode === "wiki"} label="Wiki" icon={BookOpen} onClick={() => onModeChange("wiki")} /></div>{mode === "wiki" && <Link to="/wiki" className="arc-secondary-button"><BookOpen aria-hidden /> Ouvrir le wiki salarié</Link>}{mode !== "lda" && <button type="button" className="arc-primary-button" onClick={onCreate}><Plus aria-hidden /> Nouveau document</button>}</div></header>;
}

function ModeButton({ active, label, icon: Icon, onClick }: { active: boolean; label: string; icon: typeof Library; onClick: () => void }): ReactElement {
  return <button type="button" aria-pressed={active} onClick={onClick}><Icon aria-hidden />{label}</button>;
}

function DocumentRail({ documents, selectedPath, query, mode, onQuery, onSelect }: { documents: ArcenalDocumentSummary[]; selectedPath: string; query: string; mode: KnowledgeMode; onQuery: (query: string) => void; onSelect: (path: string) => void }): ReactElement {
  return <aside className="arc-document-rail"><div className="arc-search"><Search aria-hidden /><input aria-label="Rechercher dans le coffre" value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Rechercher…" /></div><div className="arc-rail-title"><strong>{modeLabel(mode)}</strong><span>{documents.length}</span></div><div className="arc-document-list">{documents.map((document) => <button key={document.path} type="button" className={document.path === selectedPath ? "is-selected" : ""} onClick={() => onSelect(document.path)}><FilePenLine aria-hidden /><span><strong>{document.title}</strong><small>{document.reference || document.path}</small></span><i data-tone={statusTone(document.status)} title={document.status} /></button>)}{documents.length === 0 && <div className="arc-rail-empty"><Library aria-hidden /><p>Aucun document dans cette vue.</p></div>}</div></aside>;
}

function modeLabel(mode: KnowledgeMode): string {
  if (mode === "lda") return "Documents applicables";
  if (mode === "wiki") return "Publication salariés";
  return "Coffre documentaire";
}

function DocumentCanvas({ document, content, editorMode, onContent, onMode, onSave }: { document: ArcenalDocumentSummary | null; content: string; editorMode: EditorMode; onContent: (content: string) => void; onMode: (mode: EditorMode) => void; onSave: () => void }): ReactElement {
  if (!document) return <EmptyDocumentCanvas />;
  return <article className="arc-document-canvas"><header><div><span>{document.reference || "NOTE"} · v{document.version}</span><h2>{document.title}</h2></div><div className="arc-editor-actions"><button type="button" aria-pressed={editorMode === "read"} onClick={() => onMode("read")}>Lecture</button><button type="button" aria-pressed={editorMode === "edit"} onClick={() => onMode("edit")}>Édition</button>{editorMode === "edit" && <button type="button" className="save" onClick={onSave}><Save aria-hidden /> Enregistrer</button>}</div></header><div className="arc-document-body">{editorMode === "edit" ? <textarea aria-label="Contenu Markdown" value={content} onChange={(event) => onContent(event.target.value)} spellCheck /> : <Markdown content={contentWithoutFrontmatter(content)} />}</div></article>;
}

function contentWithoutFrontmatter(content: string): string {
  return content.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, "");
}

function EmptyDocumentCanvas(): ReactElement {
  return <article className="arc-document-canvas arc-empty-canvas"><Library aria-hidden /><h2>Le coffre est prêt</h2><p>Créez un document Markdown. ARC pourra ensuite le retrouver, le citer et l’inscrire dans la LDA lorsqu’il devient applicable.</p></article>;
}

function KnowledgeContext({ document, overview, mode }: { document: ArcenalDocumentSummary | null; overview: ArcenalKnowledgeOverview | null; mode: KnowledgeMode }): ReactElement {
  return <aside className="arc-knowledge-context"><section><span>État du corpus</span><div className="arc-stat-list"><Stat value={overview?.statistics.documents ?? 0} label="Documents" /><Stat value={overview?.statistics.pending ?? 0} label="À traiter" /><Stat value={overview?.statistics.overdue ?? 0} label="Revues échues" alert /></div></section>{document && <><section><span>Gouvernance</span><dl className="arc-metadata"><Meta label="Statut" value={document.status} /><Meta label="Propriétaire" value={document.owner || "Non défini"} /><Meta label="Périmètre" value={document.scope || "Non défini"} /><Meta label="Prochaine revue" value={document.review_date || "Non planifiée"} /><Meta label="Versions conservées" value={String(document.history_count)} /></dl>{document.tags.length > 0 && <div className="arc-tags">{document.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>}</section><RelationList title="Liens de la note" items={document.links} empty="Ajoutez [[Nom de note]] pour relier les connaissances." /><RelationList title="Liens entrants" items={document.backlinks} empty="Aucune note ne cite encore ce document." /></>}<section className="arc-publishing-rule"><Check aria-hidden /><p>{mode === "wiki" ? "Le wiki expose uniquement les versions applicables." : "ARC peut proposer une révision, jamais la publier sans approbation."}</p></section></aside>;
}

function RelationList({ title, items, empty }: { title: string; items: string[]; empty: string }): ReactElement {
  return <section><span>{title}</span>{items.length ? <ul className="arc-link-list">{items.map((item) => <li key={item}><GitFork aria-hidden />{item}</li>)}</ul> : <p className="arc-context-empty">{empty}</p>}</section>;
}

function Stat({ value, label, alert = false }: { value: number; label: string; alert?: boolean }): ReactElement {
  return <div className={alert && value > 0 ? "is-alert" : ""}>{alert && value > 0 && <CircleAlert aria-hidden />}<strong>{value}</strong><small>{label}</small></div>;
}

function Meta({ label, value }: { label: string; value: string }): ReactElement {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function NewDocumentDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (path: string, attached: boolean) => Promise<void> }): ReactElement {
  const [title, setTitle] = useState("");
  const [folder, setFolder] = useState("QSSERP");
  const [file, setFile] = useState<File | null>(null);
  const [fields, setFields] = useState<DocumentTemplateFields>({ changeType: "Création", revision: "1", status: "À approuver", type: "Procédure" });
  const [error, setError] = useState("");
  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const slug = slugifyDocumentTitle(title);
    if (!slug) return setError("Le titre doit contenir au moins une lettre ou un chiffre.");
    const path = `${folder.trim().replace(/^\/+|\/+$/g, "") || "Notes"}/${slug}.md`;
    const content = createDocumentTemplate(title.trim(), path, fields);
    try {
      if (file) await api.uploadArcenalDocument(path, content, file);
      else await api.createArcenalDocument(path, content);
      await onCreated(path, file !== null);
    }
    catch (cause) { setError(errorMessage(cause, "Création impossible.")); }
  };
  const update = (key: keyof DocumentTemplateFields, value: string): void => setFields((current) => ({ ...current, [key]: value }));
  const selectFile = (selected: File | null): void => {
    if (!selected) return setFile(null);
    const validation = validateLdaAttachment(selected);
    if (validation) { setFile(null); return setError(validation); }
    setFile(selected); setError("");
    setTitle((current) => current || selected.name.replace(/\.[^.]+$/, ""));
  };
  return <div className="arc-dialog-backdrop" role="presentation"><form className="arc-dialog arc-document-dialog" role="dialog" aria-modal="true" aria-labelledby="new-document-title" onSubmit={(event) => void submit(event)}><button className="arc-dialog-close" type="button" onClick={onClose} aria-label="Fermer"><X aria-hidden /></button><p>Nouveau document LDA</p><h2 id="new-document-title">Déposer une fiche documentaire</h2>{error && <span className="arc-alert arc-alert-error">{error}</span>}<label className="arc-upload-field"><Paperclip aria-hidden /><span><strong>{file?.name || "Choisir le document source"}</strong><small>PDF, DOCX, ODT, TXT ou Markdown · 20 Mio maximum</small></span><input type="file" accept={LDA_ATTACHMENT_ACCEPT} onChange={(event) => selectFile(event.target.files?.[0] ?? null)} /></label><label className="arc-field"><span>Titre</span><input autoFocus value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Gestion des habilitations" /></label><div className="arc-form-row"><DialogInput label="Dénomination" value={fields.type ?? ""} onChange={(value) => update("type", value)} placeholder="Procédure" /><DialogInput label="Activité" value={fields.activity ?? ""} onChange={(value) => update("activity", value)} placeholder="Qualité" /></div><div className="arc-form-row"><DialogInput label="Numérotation" value={fields.number ?? ""} onChange={(value) => update("number", value)} placeholder="PRO-Q-01" /><DialogInput label="Révision N°" value={fields.revision ?? ""} onChange={(value) => update("revision", value)} placeholder="1" /></div><div className="arc-form-row"><label className="arc-field"><span>Nature</span><select value={fields.changeType} onChange={(event) => update("changeType", event.target.value)}><option>Création</option><option>Révision</option></select></label><DialogInput label="Date de validation" type="date" value={fields.validationDate ?? ""} onChange={(value) => update("validationDate", value)} /></div><div className="arc-form-row"><DialogInput label="Motif" value={fields.reason ?? ""} onChange={(value) => update("reason", value)} placeholder="Motif de la version" /><label className="arc-field"><span>Statut</span><select value={fields.status} onChange={(event) => update("status", event.target.value)}><option>Brouillon</option><option>À approuver</option><option>Applicable</option></select></label></div><DialogInput label="Dossier Markdown" value={folder} onChange={setFolder} placeholder="QSSERP" /><button className="arc-primary-button" type="submit" disabled={!title.trim()}><Plus aria-hidden /> {file ? "Déposer le document" : "Créer la fiche"}</button></form></div>;
}

function DialogInput({ label, value, onChange, placeholder = "", type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string }): ReactElement {
  return <label className="arc-field"><span>{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>;
}
