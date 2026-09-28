import { Brain, History, Pencil, Plus, RotateCcw, Search, Trash2, X } from "lucide-react";
import { useEffect, useState, type Dispatch, type FormEvent, type ReactElement, type SetStateAction } from "react";
import { api, type ArcenalManagedFileVersion, type ArcenalMemoryEntry } from "@/lib/api";
import { isArcenalMemoryEntriesResponse } from "@/lib/arcenal-memory";

interface MemoryState {
  busy: boolean;
  content: string;
  editingId: string;
  entries: ArcenalMemoryEntry[];
  error: string;
  notice: string;
  query: string;
  title: string;
  versions: ArcenalManagedFileVersion[];
}

const INITIAL_STATE: MemoryState = { busy: true, content: "", editingId: "", entries: [], error: "", notice: "", query: "", title: "", versions: [] };

export function ArcenalMemorySettingsPanel(): ReactElement {
  const [state, setState] = useState<MemoryState>(INITIAL_STATE);
  useEffect(() => { void loadMemory("", setState); }, []);
  const submit = (event: FormEvent<HTMLFormElement>): void => { event.preventDefault(); void persistEntry(state, setState); };
  const search = (event: FormEvent<HTMLFormElement>): void => { event.preventDefault(); void loadMemory(state.query, setState); };
  return <section className="arc-settings-section arc-memory-settings"><MemoryHeading /><MemorySearch state={state} setState={setState} onSubmit={search} /><div className="arc-memory-layout"><MemoryForm state={state} setState={setState} onSubmit={submit} /><MemoryCatalog state={state} setState={setState} /><MemoryHistory state={state} setState={setState} /></div></section>;
}

function MemoryHeading(): ReactElement {
  return <div className="arc-settings-section-title"><span><Brain /></span><div><small>Continuité entre les sessions</small><h2>Mémoire durable d’ARC</h2><p>Conservez les décisions, préférences, conventions, projets et actions utiles, sans mélanger cette mémoire avec l’historique du chat.</p></div></div>;
}

function MemorySearch({ state, setState, onSubmit }: MemoryViewProps & { onSubmit: (event: FormEvent<HTMLFormElement>) => void }): ReactElement {
  return <form className="arc-memory-search" onSubmit={onSubmit}><Search aria-hidden /><input aria-label="Rechercher dans la mémoire" onChange={(event) => setState((current) => ({ ...current, query: event.target.value }))} placeholder="Rechercher une décision, un projet ou une convention…" value={state.query} /><button disabled={state.busy} type="submit">Rechercher</button>{state.query && <button onClick={() => { setState((current) => ({ ...current, query: "" })); void loadMemory("", setState); }} type="button">Réinitialiser</button>}</form>;
}

function MemoryForm({ state, setState, onSubmit }: MemoryViewProps & { onSubmit: (event: FormEvent<HTMLFormElement>) => void }): ReactElement {
  const reset = (): void => setState((current) => resetEditor(current));
  return <form className="arc-memory-form" onSubmit={onSubmit}><header><span>{state.editingId ? <Pencil /> : <Plus />}</span><div><strong>{state.editingId ? "Modifier l’entrée" : "Ajouter une entrée"}</strong><small>Chaque changement conserve la version précédente de MEMORY.md.</small></div>{state.editingId && <button aria-label="Annuler la modification" onClick={reset} type="button"><X /></button>}</header>{state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}{state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}<label className="arc-field"><span>Titre</span><input maxLength={160} onChange={(event) => setState((current) => ({ ...current, title: event.target.value }))} required value={state.title} /></label><label className="arc-field"><span>Contenu</span><textarea maxLength={16_000} onChange={(event) => setState((current) => ({ ...current, content: event.target.value }))} required rows={8} value={state.content} /></label><button className="arc-primary-button" disabled={state.busy || !state.title.trim() || !state.content.trim()} type="submit">{state.editingId ? "Enregistrer la modification" : "Ajouter à la mémoire"}</button></form>;
}

function MemoryCatalog({ state, setState }: MemoryViewProps): ReactElement {
  if (!state.entries.length) return <div className="arc-memory-empty"><Brain /><p>{state.busy ? "Chargement de la mémoire…" : "Aucune entrée ne correspond à cette recherche."}</p></div>;
  return <section className="arc-memory-catalog" aria-label="Entrées de mémoire">{state.entries.map((entry) => <article key={entry.id}><header><h3>{entry.title}</h3><div><button aria-label={`Modifier ${entry.title}`} onClick={() => editEntry(entry, setState)} type="button"><Pencil /></button><button aria-label={`Supprimer ${entry.title}`} disabled={state.busy} onClick={() => { void removeEntry(entry, setState); }} type="button"><Trash2 /></button></div></header><p>{entry.content}</p></article>)}</section>;
}

function MemoryHistory({ state, setState }: MemoryViewProps): ReactElement {
  return <section className="arc-managed-history arc-memory-history"><header><History /><strong>Historique de MEMORY.md</strong><span>{state.versions.length} version{state.versions.length > 1 ? "s" : ""}</span></header>{state.versions.length ? <ul>{state.versions.map((version) => <li key={version.version_id}><span><strong>{formatDate(version.updated_at)}</strong><small>{version.author || "administrateur"}</small></span><button disabled={state.busy} onClick={() => { void restoreMemory(version.version_id, setState); }} type="button"><RotateCcw /> Restaurer</button></li>)}</ul> : <p>Aucune version antérieure.</p>}</section>;
}

async function loadMemory(query: string, setState: SetMemoryState): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const [catalog, history] = await Promise.all([api.getArcenalMemoryEntries(query), api.getArcenalManagedFileHistory("memory")]);
    if (!isArcenalMemoryEntriesResponse(catalog) || !Array.isArray(history.versions)) throw new Error("La réponse mémoire d’ARC est incomplète.");
    setState((current) => ({ ...current, busy: false, entries: catalog.entries, versions: history.versions }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function persistEntry(state: MemoryState, setState: SetMemoryState): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    if (state.editingId) await api.updateArcenalMemoryEntry(state.editingId, state.title.trim(), state.content.trim());
    else await api.createArcenalMemoryEntry(state.title.trim(), state.content.trim());
    await loadMemory(state.query, setState);
    setState((current) => ({ ...resetEditor(current), notice: "La mémoire durable est enregistrée." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function removeEntry(entry: ArcenalMemoryEntry, setState: SetMemoryState): Promise<void> {
  if (!window.confirm(`Supprimer « ${entry.title} » ? La version actuelle restera restaurable.`)) return;
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    await api.deleteArcenalMemoryEntry(entry.id);
    await loadMemory("", setState);
    setState((current) => ({ ...resetEditor(current), notice: "L’entrée a été supprimée." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function restoreMemory(versionId: string, setState: SetMemoryState): Promise<void> {
  if (!window.confirm("Restaurer cette version de la mémoire ? La version actuelle sera conservée.")) return;
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    await api.restoreArcenalManagedFile("memory", versionId);
    await loadMemory("", setState);
    setState((current) => ({ ...resetEditor(current), notice: "La mémoire sélectionnée est restaurée." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

function editEntry(entry: ArcenalMemoryEntry, setState: SetMemoryState): void {
  setState((current) => ({ ...current, content: entry.content, editingId: entry.id, error: "", notice: "", title: entry.title }));
}

function resetEditor(state: MemoryState): MemoryState {
  return { ...state, busy: false, content: "", editingId: "", error: "", title: "" };
}

function formatDate(value: string): string {
  const date = new Date(value);
  return !value || Number.isNaN(date.getTime()) ? "Date inconnue" : date.toLocaleString("fr-FR");
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "La mémoire ARC est indisponible.";
}

type SetMemoryState = Dispatch<SetStateAction<MemoryState>>;
interface MemoryViewProps { setState: SetMemoryState; state: MemoryState }
