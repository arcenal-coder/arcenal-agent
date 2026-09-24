import { useCallback, useEffect, useState, type FormEvent, type ReactElement } from "react";
import { Link } from "react-router";
import { Bot, Boxes, Brain, CheckCircle2, Plus, ShieldCheck, Sparkles } from "lucide-react";
import { api, type ProfileInfo } from "@/lib/api";

interface AgentDraft {
  description: string;
  model: string;
  name: string;
  provider: string;
}

interface AgentCreatePayload {
  description: string;
  model?: string;
  name: string;
  provider?: string;
}

const EMPTY_DRAFT: AgentDraft = { description: "", model: "", name: "", provider: "openrouter" };

export default function ArcenalAgentsPage(): ReactElement {
  const [profiles, setProfiles] = useState<ProfileInfo[]>([]);
  const [active, setActive] = useState("");
  const [draft, setDraft] = useState<AgentDraft>(EMPTY_DRAFT);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async (): Promise<void> => {
    try {
      const [result, activeResult] = await Promise.all([api.getProfiles(), api.getActiveProfile()]);
      setProfiles(result.profiles);
      setActive(activeResult.active);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Chargement des agents impossible.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setCreating(true);
    setError("");
    try {
      await api.createProfile(cleanDraft(draft));
      setDraft(EMPTY_DRAFT);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Création de l’agent impossible.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="arc-workspace arc-agents" aria-labelledby="agents-title">
      <WorkspaceHeading eyebrow="Volet 2 · Fabrique d’agents" title="Des agents spécialisés, gouvernés par ARC" description="Chaque agent possède son modèle, ses compétences et sa mémoire. Les connexions aux applications seront activées par le protocole AACP/1." />
      {error && <p className="arc-alert arc-alert-error" role="alert">{error}</p>}
      <section className="arc-agent-layout">
        <div className="arc-agent-main">
          <div className="arc-panel-heading"><div><span>Agents disponibles</span><h2>{profiles.length} environnement{profiles.length === 1 ? "" : "s"}</h2></div><Link to="/profiles" className="arc-text-link">Réglages avancés</Link></div>
          <div className="arc-agent-grid">
            {profiles.map((profile) => <AgentCard key={profile.name} profile={profile} active={profile.name === active} />)}
            {profiles.length === 0 && <EmptyAgents />}
          </div>
        </div>
        <form className="arc-create-agent" onSubmit={(event) => void submit(event)}>
          <span className="arc-kicker"><Plus aria-hidden /> Nouvel agent</span>
          <h2>Définir une mission</h2>
          <Field label="Identifiant" value={draft.name} placeholder="veille-reglementaire" onChange={(name) => setDraft({ ...draft, name })} />
          <Field label="Rôle" value={draft.description} placeholder="Surveille les évolutions réglementaires…" onChange={(description) => setDraft({ ...draft, description })} />
          <div className="arc-form-row">
            <Field label="Fournisseur" value={draft.provider} placeholder="openrouter" onChange={(provider) => setDraft({ ...draft, provider })} />
            <Field label="Modèle" value={draft.model} placeholder="Modèle par défaut" onChange={(model) => setDraft({ ...draft, model })} />
          </div>
          <button className="arc-primary-button" disabled={creating || !draft.name.trim()} type="submit"><Sparkles aria-hidden />{creating ? "Création…" : "Créer l’agent"}</button>
          <small>L’agent est créé dans un profil isolé. Aucun connecteur applicatif n’est activé automatiquement.</small>
          <Link to="/settings" className="arc-provider-link">Connecter OpenRouter dans les paramètres ARCenal</Link>
        </form>
      </section>
      <ConnectorRoadmap />
    </main>
  );
}

function cleanDraft(draft: AgentDraft): AgentCreatePayload {
  return {
    name: draft.name.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "-"),
    description: draft.description.trim(),
    provider: draft.provider.trim() || undefined,
    model: draft.model.trim() || undefined,
  };
}

function AgentCard({ profile, active }: { profile: ProfileInfo; active: boolean }): ReactElement {
  return (
    <article className="arc-agent-card">
      <div className="arc-agent-avatar"><Bot aria-hidden /></div>
      <div className="arc-agent-copy"><div><h3>{profile.display_name || profile.name}</h3>{active && <span className="arc-live-badge">Actif</span>}</div><p>{profile.description || "Agent à spécialiser"}</p><dl><div><dt>Modèle</dt><dd>{profile.model || "Hérité d’ARC"}</dd></div><div><dt>Compétences</dt><dd>{profile.skill_count}</dd></div></dl></div>
      <Link to="/profiles" className="arc-card-action" aria-label={`Configurer ${profile.name}`}>Configurer</Link>
    </article>
  );
}

function EmptyAgents(): ReactElement {
  return <div className="arc-empty-state"><Brain aria-hidden /><h3>Aucun agent spécialisé</h3><p>ARC reste disponible. Créez votre premier agent métier avec le formulaire.</p></div>;
}

function Field({ label, value, placeholder, onChange }: { label: string; value: string; placeholder: string; onChange: (value: string) => void }): ReactElement {
  return <label className="arc-field"><span>{label}</span><input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>;
}

function WorkspaceHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }): ReactElement {
  return <header className="arc-workspace-heading"><p>{eyebrow}</p><h1 id="agents-title">{title}</h1><span>{description}</span></header>;
}

function ConnectorRoadmap(): ReactElement {
  const apps = ["ATS", "Nextcloud", "Veille réglementaire", "Applications ARCenal"];
  return <section className="arc-connectors"><div><span className="arc-kicker"><Boxes aria-hidden /> Connecteurs AACP/1</span><h2>Architecture prête, activation contrôlée</h2><p>Les applications pourront déléguer une mission à un agent sans lui transmettre les droits d’administration du serveur.</p></div><ul>{apps.map((app) => <li key={app}><ShieldCheck aria-hidden /><span><strong>{app}</strong><small>Connecteur à développer</small></span><CheckCircle2 aria-hidden /></li>)}</ul></section>;
}
