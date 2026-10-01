import { Archive, Brain, Clock, Eye, Pencil, Plus, RefreshCcw, Search, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState, type Dispatch, type FormEvent, type ReactElement, type SetStateAction } from "react";
import {
  api, type EnterpriseMemoryDetailResponse, type EnterpriseMemoryEntry,
  type EnterpriseMemoryFilters, type EnterpriseMemoryMetrics, type EnterpriseMemoryStatus,
  type EnterpriseMemoryType, type EnterpriseMemoryWrite,
} from "@/lib/api";

interface MemoryState {
  busy: boolean;
  correctionReason: string;
  detail: EnterpriseMemoryDetailResponse | null;
  draft: EnterpriseMemoryWrite;
  editingId: string;
  entries: EnterpriseMemoryEntry[];
  error: string;
  filters: EnterpriseMemoryFilters;
  metrics: EnterpriseMemoryMetrics | null;
  notice: string;
}

const EMPTY_DRAFT: EnterpriseMemoryWrite = {
  confidentiality: "internal", confidence: 1, content: "", expires_at: null,
  knowledge_scopes: ["company"], memory_type: "fact", person: null, project: null,
  retention_mode: "permanent", source_id: "saisie-administrateur", source_type: "manual",
  status: "active", summary: "", rule_kind: null,
};

const INITIAL_STATE: MemoryState = {
  busy: true, correctionReason: "", detail: null, draft: EMPTY_DRAFT, editingId: "", entries: [], error: "",
  filters: {}, metrics: null, notice: "",
};

const TYPE_LABELS: Record<EnterpriseMemoryType, string> = {
  decision: "Décision", fact: "Fait", person: "Personne", preference: "Préférence",
  project: "Projet", rule: "Règle",
};

const STATUS_LABELS: Record<EnterpriseMemoryStatus, string> = {
  active: "Active", archived: "Archivée", deleted: "Supprimée", expired: "Expirée",
  pending_review: "À vérifier",
};

export function ArcenalMemorySettingsPanel(): ReactElement {
  const [state, setState] = useState<MemoryState>(INITIAL_STATE);
  useEffect(() => { void loadMemory({}, setState); }, []);
  return <section className="arc-settings-section arc-memory-settings">
    <MemoryHeading /><MemoryMetrics metrics={state.metrics} />
    <MemoryFiltersBar state={state} setState={setState} />
    {state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}
    {state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}
    <div className="arc-memory-layout"><MemoryEditor state={state} setState={setState} /><MemoryCatalog state={state} setState={setState} /><MemoryDetail state={state} setState={setState} /></div>
  </section>;
}

function MemoryHeading(): ReactElement {
  return <div className="arc-settings-section-title"><span><Brain /></span><div>
    <small>Continuité gouvernée</small><h2>Mémoire d’entreprise</h2>
    <p>ARC se souvient avec une origine, des droits et un niveau d’autorité explicites. La LDA reste prioritaire.</p>
  </div></div>;
}

function MemoryMetrics({ metrics }: { metrics: EnterpriseMemoryMetrics | null }): ReactElement {
  const items = metrics ? [["Total", metrics.total], ["Actives", metrics.active], ["Archivées", metrics.archived], ["Expirées", metrics.expired], ["Injectées dans le RAG", metrics.used_by_rag]] : [];
  return <div className="arc-memory-metrics">{items.map(([label, value]) => <article key={label}><strong>{value}</strong><span>{label}</span></article>)}</div>;
}

function MemoryFiltersBar({ state, setState }: MemoryViewProps): ReactElement {
  const submit = (event: FormEvent<HTMLFormElement>): void => { event.preventDefault(); void loadMemory(state.filters, setState); };
  const update = (name: keyof EnterpriseMemoryFilters, value: string): void => setState((current) => ({ ...current, filters: { ...current.filters, [name]: value } }));
  return <form className="arc-memory-search arc-memory-filters" onSubmit={submit}><Search aria-hidden />
    <input aria-label="Rechercher dans la mémoire" onChange={(event) => update("query", event.target.value)} placeholder="Rechercher…" value={state.filters.query ?? ""} />
    <select aria-label="Filtrer par type" onChange={(event) => update("memory_type", event.target.value)} value={state.filters.memory_type ?? ""}><option value="">Tous les types</option>{Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
    <select aria-label="Filtrer par statut" onChange={(event) => update("status", event.target.value)} value={state.filters.status ?? ""}><option value="">Tous les statuts</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
    <select aria-label="Filtrer par source" onChange={(event) => update("source_type", event.target.value)} value={state.filters.source_type ?? ""}><option value="">Toutes les sources</option><option value="manual">Manuelle</option><option value="conversation">Conversation</option><option value="application">Application</option><option value="document">Document</option><option value="agent">Agent</option><option value="import">Import</option><option value="api">API</option></select>
    <select aria-label="Filtrer par confidentialité" onChange={(event) => update("confidentiality", event.target.value)} value={state.filters.confidentiality ?? ""}><option value="">Toutes confidentialités</option><option value="public">Publique</option><option value="internal">Interne</option><option value="restricted">Restreinte</option><option value="confidential">Confidentielle</option><option value="admin">Administration</option></select>
    <input aria-label="Filtrer par scope" onChange={(event) => update("scope", event.target.value)} placeholder="Scope" value={state.filters.scope ?? ""} />
    <input aria-label="Filtrer par projet" onChange={(event) => update("project", event.target.value)} placeholder="Projet" value={state.filters.project ?? ""} />
    <button disabled={state.busy} type="submit">Filtrer</button>
  </form>;
}

function MemoryEditor({ state, setState }: MemoryViewProps): ReactElement {
  const update = <K extends keyof EnterpriseMemoryWrite>(key: K, value: EnterpriseMemoryWrite[K]): void => setState((current) => ({ ...current, draft: { ...current.draft, [key]: value } }));
  const submit = (event: FormEvent<HTMLFormElement>): void => { event.preventDefault(); void persistMemory(state, setState); };
  return <form className="arc-memory-form" onSubmit={submit}><header><span>{state.editingId ? <Pencil /> : <Plus />}</span><div><strong>{state.editingId ? "Corriger la mémoire" : "Créer une mémoire"}</strong><small>Une origine est obligatoire et chaque correction est historisée.</small></div></header>
    <Field label="Résumé"><input maxLength={500} onChange={(event) => update("summary", event.target.value)} required value={state.draft.summary} /></Field>
    <Field label="Contenu"><textarea maxLength={16000} onChange={(event) => update("content", event.target.value)} required rows={5} value={state.draft.content} /></Field>
    <div className="arc-form-row"><SelectField label="Type" value={state.draft.memory_type} onChange={(value) => update("memory_type", value as EnterpriseMemoryType)} options={TYPE_LABELS} /><Field label="Scopes"><input onChange={(event) => update("knowledge_scopes", splitValues(event.target.value))} value={state.draft.knowledge_scopes.join(", ")} /></Field></div>
    <div className="arc-form-row"><SelectField label="Type d’origine" value={state.draft.source_type} onChange={(value) => update("source_type", value as EnterpriseMemoryWrite["source_type"])} options={{ manual: "Manuelle", conversation: "Conversation", application: "Application", document: "Document", agent: "Agent", import: "Import", api: "API" }} /><Field label="Identifiant d’origine"><input onChange={(event) => update("source_id", event.target.value)} required value={state.draft.source_id} /></Field></div>
    <div className="arc-form-row"><Field label="Auteur de l’origine"><input onChange={(event) => update("source_author", nullable(event.target.value))} value={state.draft.source_author ?? ""} /></Field><Field label="Date de l’origine"><input onChange={(event) => update("source_recorded_at", event.target.value ? new Date(event.target.value).toISOString() : null)} type="datetime-local" value={dateTimeInput(state.draft.source_recorded_at)} /></Field></div>
    <Field label="Projet"><input onChange={(event) => update("project", nullable(event.target.value))} value={state.draft.project ?? ""} /></Field>
    <div className="arc-form-row"><SelectField label="Confidentialité" value={state.draft.confidentiality} onChange={(value) => update("confidentiality", value as EnterpriseMemoryWrite["confidentiality"])} options={{ public: "Publique", internal: "Interne", restricted: "Restreinte", confidential: "Confidentielle", admin: "Administration" }} /><Field label="Expiration"><input disabled={state.draft.retention_mode === "permanent"} onChange={(event) => update("expires_at", event.target.value ? new Date(event.target.value).toISOString() : null)} type="date" value={dateInput(state.draft.expires_at)} /></Field></div>
    <label className="arc-memory-retention"><input checked={state.draft.retention_mode === "permanent"} onChange={(event) => update("retention_mode", event.target.checked ? "permanent" : "expiring")} type="checkbox" /> Conservation permanente</label>
    <div className="arc-form-row"><Field label="Applications autorisées"><input onChange={(event) => update("allowed_applications", splitValues(event.target.value))} placeholder="arcenal-ats, qss-erp" value={(state.draft.allowed_applications ?? []).join(", ")} /></Field><Field label="Agents autorisés"><input onChange={(event) => update("allowed_agents", splitValues(event.target.value))} placeholder="arc, ats" value={(state.draft.allowed_agents ?? []).join(", ")} /></Field></div>
    <Field label="Utilisateurs autorisés"><input onChange={(event) => update("allowed_users", splitValues(event.target.value))} placeholder="admin, utilisateur" value={(state.draft.allowed_users ?? []).join(", ")} /></Field>
    {state.draft.memory_type === "rule" && <SelectField label="Nature de la règle" value={state.draft.rule_kind ?? "observed"} onChange={(value) => update("rule_kind", value as NonNullable<EnterpriseMemoryWrite["rule_kind"]>)} options={{ observed: "Observée", business: "Métier", derived: "Dérivée", official_reference: "Référence officielle" }} />}
    <TypedFields draft={state.draft} update={update} />
    {state.editingId && <Field label="Raison de la correction"><input onChange={(event) => setState((current) => ({ ...current, correctionReason: event.target.value }))} required value={state.correctionReason} /></Field>}
    <button className="arc-primary-button" disabled={state.busy} type="submit">{state.editingId ? "Enregistrer la correction" : "Créer la mémoire"}</button>
  </form>;
}

function MemoryCatalog({ state, setState }: MemoryViewProps): ReactElement {
  if (!state.entries.length) return <div className="arc-memory-empty"><Brain /><p>{state.busy ? "Chargement…" : "Aucune mémoire ne correspond aux filtres."}</p></div>;
  return <div className="arc-memory-catalog">{state.entries.map((entry) => <article key={entry.id}><header><div><span className={`arc-memory-status is-${entry.status}`}>{STATUS_LABELS[entry.status]}</span><small>{TYPE_LABELS[entry.memory_type]}</small></div><div><button aria-label={`Voir ${entry.summary}`} onClick={() => void openDetail(entry.id, setState)} type="button"><Eye /></button><button aria-label={`Modifier ${entry.summary}`} onClick={() => editMemory(entry, setState)} type="button"><Pencil /></button></div></header><h3>{entry.summary}</h3><p>{entry.content}</p><footer><span>{entry.knowledge_scopes.join(" · ")}</span><span>{entry.confidentiality}</span></footer></article>)}</div>;
}

function MemoryDetail({ state, setState }: MemoryViewProps): ReactElement | null {
  const entry = state.detail?.entry;
  if (!entry) return null;
  return <aside className="arc-memory-detail"><header><div><small>Fiche mémoire · V{entry.version}</small><h3>{entry.summary}</h3></div><button aria-label="Fermer la fiche" onClick={() => setState((current) => ({ ...current, detail: null }))} type="button">×</button></header>
    <p className="arc-memory-detail-content">{entry.content}</p>
    <dl><Fact label="Type et statut" value={`${TYPE_LABELS[entry.memory_type]} · ${STATUS_LABELS[entry.status]}`} /><Fact label="Origine" value={`${entry.provenance.source_type} · ${entry.provenance.source_id}`} /><Fact label="Auteur" value={entry.provenance.author ?? entry.created_by} /><Fact label="Date de l’origine" value={formatDate(entry.provenance.recorded_at)} /><Fact label="Portée" value={entry.knowledge_scopes.join(", ")} /><Fact label="Confidentialité" value={entry.confidentiality} /><Fact label="Accès ciblés" value={[...entry.allowed_applications, ...entry.allowed_agents, ...entry.allowed_users].join(", ") || "ACL par portée"} /><Fact label="Création" value={formatDate(entry.created_at)} /><Fact label="Modification" value={formatDate(entry.updated_at)} /><Fact label="Revue" value={entry.review_date ? formatDate(entry.review_date) : "Non planifiée"} /><Fact label="Expiration" value={entry.expires_at ? formatDate(entry.expires_at) : "Permanente"} /><Fact label="Relations" value={entry.relations.map((relation) => `${relation.target_kind}:${relation.target_id}`).join(", ") || "Aucune"} /></dl>
    <div className="arc-memory-actions">{entry.status !== "deleted" && <MemoryLifecycleActions entry={entry} setState={setState} />}<button onClick={() => void forgetMemory(entry, setState)} type="button"><Trash2 />Droit à l’oubli</button></div>
    <section><h4><ShieldCheck />Historique de correction</h4>{state.detail?.history.length ? <ul>{state.detail.history.map((revision) => <li key={revision.id}><strong>Version {revision.version}</strong><span>{revision.reason}</span><small>{revision.corrected_by} · {formatDate(revision.corrected_at)}</small></li>)}</ul> : <p>Aucune correction.</p>}</section>
  </aside>;
}

function Field({ children, label }: { children: ReactElement; label: string }): ReactElement {
  return <label className="arc-field"><span>{label}</span>{children}</label>;
}

function SelectField({ label, onChange, options, value }: { label: string; onChange: (value: string) => void; options: Record<string, string>; value: string }): ReactElement {
  return <label className="arc-field"><span>{label}</span><select onChange={(event) => onChange(event.target.value)} value={value}>{Object.entries(options).map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label>;
}

function Fact({ label, value }: { label: string; value: string }): ReactElement {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function TypedFields({ draft, update }: { draft: EnterpriseMemoryWrite; update: DraftUpdater }): ReactElement | null {
  if (draft.memory_type === "decision") return <><Field label="Contexte de décision"><textarea onChange={(event) => update("decision_context", nullable(event.target.value))} value={draft.decision_context ?? ""} /></Field><div className="arc-form-row"><Field label="Motif"><input onChange={(event) => update("decision_reason", nullable(event.target.value))} value={draft.decision_reason ?? ""} /></Field><Field label="Décideur"><input onChange={(event) => update("decision_maker", nullable(event.target.value))} value={draft.decision_maker ?? ""} /></Field></div><Field label="Date de revue"><input onChange={(event) => update("review_date", event.target.value ? new Date(event.target.value).toISOString() : null)} type="date" value={dateInput(draft.review_date ?? null)} /></Field></>;
  if (draft.memory_type === "person") return <><div className="arc-form-row"><Field label="Service"><input onChange={(event) => update("person_service", nullable(event.target.value))} value={draft.person_service ?? ""} /></Field><Field label="Rôle professionnel"><input onChange={(event) => update("person_role", nullable(event.target.value))} value={draft.person_role ?? ""} /></Field></div><Field label="Responsabilités"><input onChange={(event) => update("responsibilities", splitValues(event.target.value))} value={(draft.responsibilities ?? []).join(", ")} /></Field></>;
  if (draft.memory_type === "project") return <Field label="Statut du projet"><input onChange={(event) => update("project_status", nullable(event.target.value))} value={draft.project_status ?? ""} /></Field>;
  if (draft.memory_type === "preference") return <><div className="arc-form-row"><Field label="Propriétaire"><input onChange={(event) => update("preference_owner", nullable(event.target.value))} value={draft.preference_owner ?? ""} /></Field><Field label="Portée de préférence"><input onChange={(event) => update("preference_scope", nullable(event.target.value))} value={draft.preference_scope ?? ""} /></Field></div><Field label="Contexte d’application"><input onChange={(event) => update("preference_context", nullable(event.target.value))} value={draft.preference_context ?? ""} /></Field></>;
  if (draft.memory_type === "rule" && draft.rule_kind === "official_reference") return <Field label="Référence documentaire officielle"><input onChange={(event) => update("official_reference", nullable(event.target.value))} required value={draft.official_reference ?? ""} /></Field>;
  return null;
}

function MemoryLifecycleActions({ entry, setState }: { entry: EnterpriseMemoryEntry; setState: SetMemoryState }): ReactElement {
  const restore = entry.status === "archived" || entry.status === "expired";
  return <><button onClick={() => void changeStatus(entry, restore ? "active" : "archived", setState)} type="button">{restore ? <RefreshCcw /> : <Archive />}{restore ? "Réactiver" : "Archiver"}</button><button onClick={() => void changeStatus(entry, "expired", setState)} type="button"><Clock />Forcer l’expiration</button><button onClick={() => void deleteLogically(entry, setState)} type="button"><Trash2 />Supprimer</button></>;
}

async function loadMemory(filters: EnterpriseMemoryFilters, setState: SetMemoryState): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "" }));
  try {
    const [catalog, metrics] = await Promise.all([api.getEnterpriseMemories(filters), api.getEnterpriseMemoryMetrics()]);
    setState((current) => ({ ...current, busy: false, entries: catalog.entries, metrics }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function persistMemory(state: MemoryState, setState: SetMemoryState): Promise<void> {
  const reason = state.correctionReason.trim();
  const draft = state.draft.memory_type === "rule" && !state.draft.rule_kind ? { ...state.draft, rule_kind: "observed" as const } : state.draft;
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    if (state.editingId) await api.correctEnterpriseMemory(state.editingId, { ...draft, reason });
    else await api.createEnterpriseMemory(draft);
    await loadMemory(state.filters, setState);
    setState((current) => ({ ...current, correctionReason: "", draft: EMPTY_DRAFT, editingId: "", notice: "La mémoire gouvernée est enregistrée." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function openDetail(memoryId: string, setState: SetMemoryState): Promise<void> {
  try {
    const detail = await api.getEnterpriseMemory(memoryId);
    setState((current) => ({ ...current, detail, error: "" }));
  } catch (cause) {
    setState((current) => ({ ...current, error: errorMessage(cause) }));
  }
}

async function changeStatus(entry: EnterpriseMemoryEntry, status: EnterpriseMemoryStatus, setState: SetMemoryState): Promise<void> {
  const reason = window.prompt("Motif de cette action :")?.trim();
  if (!reason) return;
  await runAction(() => api.transitionEnterpriseMemory(entry.id, status, reason), "Le statut de la mémoire est actualisé.", setState);
}

async function forgetMemory(entry: EnterpriseMemoryEntry, setState: SetMemoryState): Promise<void> {
  if (!window.confirm(`Effacer définitivement « ${entry.summary} » de la source et de l’index ?`)) return;
  const reason = window.prompt("Motif du droit à l’oubli :")?.trim();
  if (!reason) return;
  await runAction(() => api.deleteEnterpriseMemory(entry.id, true, reason), "La mémoire a été physiquement supprimée.", setState);
}

async function deleteLogically(entry: EnterpriseMemoryEntry, setState: SetMemoryState): Promise<void> {
  const reason = window.prompt("Motif de la suppression logique :")?.trim();
  if (!reason) return;
  await runAction(() => api.deleteEnterpriseMemory(entry.id, false, reason), "La mémoire est supprimée des usages actifs.", setState);
}

async function runAction(action: () => Promise<unknown>, notice: string, setState: SetMemoryState): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    await action();
    await loadMemory({}, setState);
    setState((current) => ({ ...current, detail: null, notice }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

function editMemory(entry: EnterpriseMemoryEntry, setState: SetMemoryState): void {
  const draft: EnterpriseMemoryWrite = { confidentiality: entry.confidentiality, confidence: entry.confidence, content: entry.content, decision_context: entry.decision_context, decision_maker: entry.decision_maker, decision_reason: entry.decision_reason, expires_at: entry.expires_at, knowledge_scopes: entry.knowledge_scopes, memory_type: entry.memory_type, official_reference: entry.official_reference, person: entry.person, person_role: entry.person_role, person_service: entry.person_service, preference_context: entry.preference_context, preference_owner: entry.preference_owner, preference_scope: entry.preference_scope, project: entry.project, project_status: entry.project_status, relations: entry.relations, responsibilities: entry.responsibilities, retention_mode: entry.retention_mode, review_date: entry.review_date, rule_kind: entry.rule_kind, source_author: entry.provenance.author, source_id: entry.provenance.source_id, source_recorded_at: entry.provenance.recorded_at, source_type: entry.provenance.source_type, status: entry.status, summary: entry.summary };
  setState((current) => ({ ...current, correctionReason: "", draft, editingId: entry.id, error: "", notice: "" }));
}

function splitValues(value: string): string[] { return [...new Set(value.split(",").map((item) => item.trim().toLowerCase()).filter(Boolean))]; }
function nullable(value: string): string | null { return value.trim() || null; }
function dateInput(value: string | null): string { return value ? value.slice(0, 10) : ""; }
function dateTimeInput(value: string | null | undefined): string { return value ? value.slice(0, 16) : ""; }
function formatDate(value: string): string { return new Date(value).toLocaleString("fr-FR"); }
function errorMessage(cause: unknown): string { return cause instanceof Error ? cause.message : "La mémoire d’entreprise est indisponible."; }

type SetMemoryState = Dispatch<SetStateAction<MemoryState>>;
type DraftUpdater = <K extends keyof EnterpriseMemoryWrite>(key: K, value: EnterpriseMemoryWrite[K]) => void;
interface MemoryViewProps { setState: SetMemoryState; state: MemoryState }
