import { FileText, History, RotateCcw, Save, ShieldCheck } from "lucide-react";
import { useEffect, useState, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { Markdown } from "@/components/Markdown";
import { api, type ArcenalManagedFileCategory, type ArcenalManagedFileDetail, type ArcenalManagedFileSummary, type ArcenalManagedFileVersion } from "@/lib/api";

interface ManagedFilesProps {
  category: ArcenalManagedFileCategory;
}

interface ManagedFilesState {
  activeId: string;
  busy: boolean;
  content: string;
  detail: ArcenalManagedFileDetail | null;
  error: string;
  files: ArcenalManagedFileSummary[];
  mode: "edit" | "preview";
  notice: string;
  versions: ArcenalManagedFileVersion[];
}

const INITIAL_STATE: ManagedFilesState = { activeId: "", busy: true, content: "", detail: null, error: "", files: [], mode: "edit", notice: "", versions: [] };

export function ArcenalManagedFilesSettingsPanel({ category }: ManagedFilesProps): ReactElement {
  const [state, setState] = useState<ManagedFilesState>(INITIAL_STATE);
  useEffect(() => subscribeCatalog(category, setState), [category]);
  const select = (fileId: string): void => { void selectManagedFile(fileId, setState); };
  const save = (): void => { void saveManagedFile(state, setState); };
  const restore = (versionId: string): void => { void restoreManagedFile(state, versionId, setState); };
  return <section className="arc-settings-section arc-managed-settings"><ManagedHeading category={category} /><div className="arc-managed-layout"><ManagedNavigation files={state.files} activeId={state.activeId} onSelect={select} /><div className="arc-managed-editor">{state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}{state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}{state.detail ? <><ManagedToolbar state={state} setState={setState} onSave={save} /><ManagedContent state={state} setState={setState} /><ManagedHistory versions={state.versions} busy={state.busy} onRestore={restore} /></> : <ManagedEmpty busy={state.busy} />}</div></div></section>;
}

function ManagedHeading({ category }: ManagedFilesProps): ReactElement {
  const context = category === "context";
  return <div className="arc-settings-section-title"><span>{context ? <FileText /> : <ShieldCheck />}</span><div><small>{context ? "Connaissance organisationnelle" : "Gouvernance"}</small><h2>{context ? "Contexte d’ARC" : "Directives d’ARC"}</h2><p>{context ? "Décrivez uniquement les informations durables nécessaires aux réponses d’ARC." : "Administrez les règles explicites sans ouvrir l’accès à d’autres fichiers du serveur."}</p></div></div>;
}

function ManagedNavigation({ files, activeId, onSelect }: { files: ArcenalManagedFileSummary[]; activeId: string; onSelect: (fileId: string) => void }): ReactElement {
  return <nav aria-label="Fichiers administrés" className="arc-managed-navigation">{files.map((file) => <button aria-pressed={file.id === activeId} key={file.id} onClick={() => onSelect(file.id)} type="button"><FileText aria-hidden /><span><strong>{file.filename}</strong><small>{file.role}</small></span><em>{file.status}</em></button>)}</nav>;
}

function ManagedToolbar({ state, setState, onSave }: { state: ManagedFilesState; setState: SetManagedState; onSave: () => void }): ReactElement {
  const file = state.detail?.file;
  return <header className="arc-managed-toolbar"><div><span>{file?.label}</span><h3>{file?.filename}</h3><small>{metadataText(file)}</small></div><div><button aria-pressed={state.mode === "edit"} onClick={() => setState((current) => ({ ...current, mode: "edit" }))} type="button">Édition</button><button aria-pressed={state.mode === "preview"} onClick={() => setState((current) => ({ ...current, mode: "preview" }))} type="button">Aperçu</button><button className="arc-primary-button" disabled={state.busy} onClick={onSave} type="button"><Save aria-hidden /> Enregistrer</button></div></header>;
}

function ManagedContent({ state, setState }: { state: ManagedFilesState; setState: SetManagedState }): ReactElement {
  if (state.mode === "preview") return <div className="arc-managed-preview"><Markdown content={state.content} /></div>;
  return <textarea aria-label={`Contenu de ${state.detail?.file.filename ?? "ce fichier"}`} className="arc-managed-textarea" maxLength={1_048_576} onChange={(event) => setState((current) => ({ ...current, content: event.target.value }))} spellCheck value={state.content} />;
}

function ManagedHistory({ versions, busy, onRestore }: { versions: ArcenalManagedFileVersion[]; busy: boolean; onRestore: (versionId: string) => void }): ReactElement {
  return <section className="arc-managed-history"><header><History aria-hidden /><strong>Historique</strong><span>{versions.length} version{versions.length > 1 ? "s" : ""}</span></header>{versions.length ? <ul>{versions.map((version) => <li key={version.version_id}><span><strong>{formatDate(version.updated_at)}</strong><small>{version.author || "administrateur"}</small></span><button disabled={busy} onClick={() => onRestore(version.version_id)} type="button"><RotateCcw aria-hidden /> Restaurer</button></li>)}</ul> : <p>Aucune version antérieure.</p>}</section>;
}

function ManagedEmpty({ busy }: { busy: boolean }): ReactElement {
  return <div className="arc-managed-empty"><FileText aria-hidden /><p>{busy ? "Chargement des fichiers administrés…" : "Aucun fichier disponible."}</p></div>;
}

function subscribeCatalog(category: ArcenalManagedFileCategory, setState: SetManagedState): () => void {
  let active = true;
  api.getArcenalManagedFiles(category).then((response) => {
    if (!active) return;
    setState((current) => ({ ...current, files: response.files, busy: false }));
    if (response.files[0]) void selectManagedFile(response.files[0].id, setState);
  }).catch((cause: unknown) => { if (active) setState((current) => ({ ...current, busy: false, error: errorMessage(cause) })); });
  return () => { active = false; };
}

async function selectManagedFile(fileId: string, setState: SetManagedState): Promise<void> {
  setState((current) => ({ ...current, activeId: fileId, busy: true, error: "", notice: "" }));
  try {
    const [detail, history] = await Promise.all([api.getArcenalManagedFile(fileId), api.getArcenalManagedFileHistory(fileId)]);
    setState((current) => ({ ...current, busy: false, content: detail.content, detail, versions: history.versions }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function saveManagedFile(state: ManagedFilesState, setState: SetManagedState): Promise<void> {
  if (!state.activeId) return;
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    await api.saveArcenalManagedFile(state.activeId, state.content);
    await selectManagedFile(state.activeId, setState);
    setState((current) => ({ ...current, notice: "Le fichier est enregistré et sa version précédente est conservée." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function restoreManagedFile(state: ManagedFilesState, versionId: string, setState: SetManagedState): Promise<void> {
  if (!state.activeId || !window.confirm("Restaurer cette version ? Le contenu actuel sera conservé dans l’historique.")) return;
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    await api.restoreArcenalManagedFile(state.activeId, versionId);
    await selectManagedFile(state.activeId, setState);
    setState((current) => ({ ...current, notice: "La version sélectionnée est restaurée." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

function metadataText(file: ArcenalManagedFileSummary | undefined): string {
  if (!file) return "";
  if (!file.updated_at) return `${file.status} · aucun enregistrement`;
  return `${file.status} · ${file.author || "administrateur"} · ${formatDate(file.updated_at)}`;
}

function formatDate(value: string): string {
  if (!value) return "Date inconnue";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date inconnue" : date.toLocaleString("fr-FR");
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Les fichiers administrés sont indisponibles.";
}

type SetManagedState = Dispatch<SetStateAction<ManagedFilesState>>;
