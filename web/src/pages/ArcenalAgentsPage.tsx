import { useCallback, useEffect, useState, type FormEvent, type ReactElement } from "react";
import { Bot, Boxes, Brain, CheckCircle2, Plus, ShieldCheck, Trash2, X } from "lucide-react";
import { ArcenalAgentForm } from "@/components/ArcenalAgentForm";
import { ArcenalCoreAgentsPanel } from "@/components/ArcenalCoreAgentsPanel";
import { api, type ProfileInfo } from "@/lib/api";
import { emptyAgentDraft, specializedProfiles, type AgentDraft } from "@/lib/arcenal-agents";
import {
  createSpecializedAgent,
  loadAgentCatalog,
  loadSpecializedAgent,
  saveSpecializedAgent,
  type AgentCatalog,
} from "@/lib/arcenal-agent-service";

const EMPTY_CATALOG: AgentCatalog = { models: {}, skills: [], toolsets: [] };

export default function ArcenalAgentsPage(): ReactElement {
  const [profiles, setProfiles] = useState<ProfileInfo[]>([]);
  const [catalog, setCatalog] = useState<AgentCatalog>(EMPTY_CATALOG);
  const [dialog, setDialog] = useState<"create" | "edit" | null>(null);
  const [draft, setDraft] = useState<AgentDraft>(emptyAgentDraft());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async (): Promise<void> => {
    try {
      const [profileResult, catalogResult] = await Promise.all([api.getProfiles(), loadAgentCatalog()]);
      setProfiles(specializedProfiles(profileResult.profiles));
      setCatalog(catalogResult);
      setError("");
    } catch (cause) {
      setError(errorMessage(cause, "Chargement des agents impossible."));
    }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const openCreate = (): void => {
    setDraft(emptyAgentDraft(catalog.models.provider ?? catalog.models.providers?.[0]?.slug));
    setDialog("create");
  };
  const openEdit = async (profile: ProfileInfo): Promise<void> => runBusy(async () => {
    const loaded = await loadSpecializedAgent(profile);
    setDraft(loaded.draft);
    setCatalog(loaded.catalog);
    setDialog("edit");
  }, setBusy, setError);
  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    await runBusy(async () => {
      if (dialog === "create") await createSpecializedAgent(draft);
      else await saveSpecializedAgent(draft, catalog);
      setDialog(null);
      await load();
    }, setBusy, setError);
  };
  const remove = async (): Promise<void> => {
    if (!window.confirm(`Supprimer définitivement l’agent ${draft.name} ?`)) return;
    await runBusy(async () => { await api.deleteProfile(draft.name); setDialog(null); await load(); }, setBusy, setError);
  };
  return <AgentsWorkspace profiles={profiles} catalog={catalog} draft={draft} dialog={dialog} busy={busy} error={error} onCreate={openCreate} onEdit={openEdit} onChange={setDraft} onClose={() => setDialog(null)} onSubmit={submit} onDelete={remove} />;
}

interface WorkspaceProps {
  profiles: ProfileInfo[]; catalog: AgentCatalog; draft: AgentDraft; dialog: "create" | "edit" | null;
  busy: boolean; error: string; onCreate: () => void; onEdit: (profile: ProfileInfo) => Promise<void>;
  onChange: (draft: AgentDraft) => void; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; onDelete: () => Promise<void>;
}

function AgentsWorkspace(props: WorkspaceProps): ReactElement {
  return (
    <main className="arc-workspace arc-agents" aria-labelledby="agents-title">
      <WorkspaceHeading />
      {props.error && <p className="arc-alert arc-alert-error" role="alert">{props.error}</p>}
      <ArcenalCoreAgentsPanel />
      <section className="arc-agent-main arc-agent-inventory">
        <InventoryHeading count={props.profiles.length} onCreate={props.onCreate} />
        <div className="arc-agent-grid">
          {props.profiles.map((profile) => <AgentCard key={profile.name} profile={profile} onEdit={props.onEdit} />)}
          {props.profiles.length === 0 && <EmptyAgents />}
        </div>
      </section>
      <ConnectorRoadmap />
      {props.dialog && <AgentDialog {...props} mode={props.dialog} />}
    </main>
  );
}

function AgentDialog(props: WorkspaceProps & { mode: "create" | "edit" }): ReactElement {
  return (
    <div className="arc-agent-modal" role="dialog" aria-modal="true" aria-labelledby="agent-dialog-title">
      <section>
        <header><div><span>{props.mode === "create" ? "Nouvel agent" : "Administration"}</span><h2 id="agent-dialog-title">{props.mode === "create" ? "Créer un spécialiste" : props.draft.name}</h2></div><button type="button" onClick={props.onClose} aria-label="Fermer"><X aria-hidden /></button></header>
        <ArcenalAgentForm busy={props.busy} catalog={props.catalog} draft={props.draft} mode={props.mode} onChange={props.onChange} onSubmit={props.onSubmit} />
        {props.mode === "edit" && <button className="arc-danger-button" disabled={props.busy} type="button" onClick={() => void props.onDelete()}><Trash2 aria-hidden /> Supprimer cet agent</button>}
      </section>
    </div>
  );
}

function InventoryHeading({ count, onCreate }: { count: number; onCreate: () => void }): ReactElement {
  return <div className="arc-panel-heading"><div><span>Profils Hermes spécialisés</span><h2>{count} profil{count === 1 ? "" : "s"} d’exécution</h2></div><button className="arc-primary-button" type="button" onClick={onCreate}><Plus aria-hidden />Créer un profil</button></div>;
}

function AgentCard({ profile, onEdit }: { profile: ProfileInfo; onEdit: (profile: ProfileInfo) => Promise<void> }): ReactElement {
  return (
    <article className="arc-agent-card">
      <div className="arc-agent-avatar"><Bot aria-hidden /></div>
      <div className="arc-agent-copy"><div><h3>{profile.display_name || profile.name}</h3><span className="arc-live-badge">{profile.gateway_running ? "Actif" : "Prêt"}</span></div><p>{profile.description || "Agent à spécialiser"}</p><dl><div><dt>Modèle</dt><dd>{profile.model || "À définir"}</dd></div><div><dt>Compétences</dt><dd>{profile.skill_count}</dd></div></dl></div>
      <button className="arc-card-action" type="button" onClick={() => void onEdit(profile)}>Administrer</button>
    </article>
  );
}

function EmptyAgents(): ReactElement {
  return <div className="arc-empty-state"><Brain aria-hidden /><h3>Aucun agent spécialisé</h3><p>Créez un agent métier avec une mission, une mémoire et des droits strictement isolés.</p></div>;
}

function WorkspaceHeading(): ReactElement {
  return <header className="arc-workspace-heading"><p>Volet 2 · Fabrique d’agents</p><h1 id="agents-title">Des agents spécialisés, gouvernés par ARC</h1><span>Chaque spécialiste possède sa propre identité, ses modèles, ses compétences, ses outils et sa mémoire.</span></header>;
}

function ConnectorRoadmap(): ReactElement {
  const apps = ["ATS", "Nextcloud", "Veille réglementaire", "Applications ARCenal"];
  return <section className="arc-connectors"><div><span className="arc-kicker"><Boxes aria-hidden /> Connecteurs AACP/1</span><h2>Architecture prête, connecteurs désactivés</h2><p>Une future application pourra déléguer une mission sans transmettre les droits d’administration du serveur.</p></div><ul>{apps.map((app) => <li key={app}><ShieldCheck aria-hidden /><span><strong>{app}</strong><small>Contrat futur AACP/1</small></span><CheckCircle2 aria-hidden /></li>)}</ul></section>;
}

async function runBusy(action: () => Promise<void>, setBusy: (value: boolean) => void, setError: (value: string) => void): Promise<void> {
  setBusy(true);
  setError("");
  try { await action(); }
  catch (cause) { setError(errorMessage(cause, "Opération impossible.")); }
  finally { setBusy(false); }
}

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}
