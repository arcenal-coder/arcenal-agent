import { useCallback, useEffect, useState, type ReactElement } from "react";
import { Bot, ShieldCheck, X } from "lucide-react";
import { loadManagedAgents, updateManagedAgent, type AgentAutonomy, type ManagedAgent } from "@/lib/arcenal-agent-manager";

const AUTONOMY_LABELS: Record<AgentAutonomy, string> = {
  approval_required: "Validation requise",
  automatic: "Automatique",
  controlled: "Contrôlée",
};

export function ArcenalCoreAgentsPanel(): ReactElement {
  const state = useManagedAgents();
  return (
    <section className="arc-agent-main arc-core-agents">
      <PanelHeading count={state.agents.length} />
      {state.error && <p className="arc-alert arc-alert-error">{state.error}</p>}
      <div className="arc-agent-grid">
        {state.agents.map((agent) => <ManagedAgentCard agent={agent} key={agent.id} onOpen={state.setSelected} />)}
      </div>
      {state.selected && <ManagedAgentDialog agent={state.selected} onClose={() => state.setSelected(null)} onSave={state.save} />}
    </section>
  );
}

function useManagedAgents(): ManagedAgentsState {
  const [agents, setAgents] = useState<ManagedAgent[]>([]);
  const [selected, setSelected] = useState<ManagedAgent | null>(null);
  const [error, setError] = useState("");
  const load = useCallback((): Promise<void> => refreshAgents(setAgents, setError), []);
  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);
  const save = (update: ManagedAgentUpdate): Promise<void> => persistAgent(selected, update, setSelected, load, setError);
  return { agents, error, save, selected, setSelected };
}

interface ManagedAgentsState {
  agents: ManagedAgent[];
  error: string;
  save: (update: ManagedAgentUpdate) => Promise<void>;
  selected: ManagedAgent | null;
  setSelected: (agent: ManagedAgent | null) => void;
}

type ManagedAgentUpdate = { autonomy_level?: AgentAutonomy; enabled?: boolean };

async function refreshAgents(setAgents: (agents: ManagedAgent[]) => void, setError: (error: string) => void): Promise<void> {
  try {
    setAgents(await loadManagedAgents());
    setError("");
  } catch (cause) {
    setError(errorMessage(cause));
  }
}

async function persistAgent(agent: ManagedAgent | null, update: ManagedAgentUpdate, setSelected: (agent: ManagedAgent) => void, reload: () => Promise<void>, setError: (error: string) => void): Promise<void> {
  if (!agent) return;
  try {
    setSelected(await updateManagedAgent(agent.id, update));
    await reload();
  } catch (cause) {
    setError(errorMessage(cause));
  }
}

function PanelHeading({ count }: { count: number }): ReactElement {
  return (
    <div className="arc-panel-heading">
      <div><span>ARC Core · Agent Manager</span><h2>{count} agent{count === 1 ? "" : "s"} gouverné{count === 1 ? "" : "s"}</h2></div>
      <ShieldCheck aria-hidden />
    </div>
  );
}

function ManagedAgentCard({ agent, onOpen }: { agent: ManagedAgent; onOpen: (agent: ManagedAgent) => void }): ReactElement {
  return (
    <article className="arc-agent-card">
      <div className="arc-agent-avatar"><Bot aria-hidden /></div>
      <div className="arc-agent-copy">
        <div><h3>{agent.name}</h3><span className={agent.enabled ? "arc-live-badge" : "arc-status-disabled"}>{agent.enabled ? "Actif" : "Désactivé"}</span></div>
        <p>{agent.description}</p>
        <dl>
          <div><dt>Identifiant</dt><dd>{agent.id}</dd></div>
          <div><dt>Application</dt><dd>{agent.application}</dd></div>
          <div><dt>Rôle</dt><dd>{agent.role}</dd></div>
          <div><dt>Autonomie</dt><dd>{AUTONOMY_LABELS[agent.autonomy_level]}</dd></div>
          <div><dt>Modèle</dt><dd>{agent.model_policy.mode === "auto" ? "Automatique" : "Fixe"}</dd></div>
          <div><dt>Connaissances</dt><dd>{agent.knowledge_scopes.join(", ")}</dd></div>
        </dl>
      </div>
      <button className="arc-card-action" type="button" onClick={() => onOpen(agent)}>Ouvrir la fiche</button>
    </article>
  );
}

function ManagedAgentDialog({ agent, onClose, onSave }: { agent: ManagedAgent; onClose: () => void; onSave: (update: ManagedAgentUpdate) => Promise<void> }): ReactElement {
  return (
    <div className="arc-agent-modal" role="dialog" aria-modal="true" aria-labelledby="core-agent-title">
      <section>
        <header><div><span>{agent.id} · {agent.application}</span><h2 id="core-agent-title">{agent.name}</h2></div><button type="button" onClick={onClose} aria-label="Fermer"><X aria-hidden /></button></header>
        <p>{agent.description}</p>
        <AgentFacts agent={agent} />
        <label className="arc-agent-setting">Autonomie<select value={agent.autonomy_level} onChange={(event) => void onSave({ autonomy_level: event.target.value as AgentAutonomy })}>{Object.entries(AUTONOMY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="arc-agent-setting"><input checked={agent.enabled} type="checkbox" onChange={(event) => void onSave({ enabled: event.target.checked })} /> Agent activé</label>
      </section>
    </div>
  );
}

function AgentFacts({ agent }: { agent: ManagedAgent }): ReactElement {
  const facts = [["Rôle", agent.role], ["Permissions", agent.permissions.join(", ") || "Aucune"], ["Outils", agent.tools.join(", ") || "Aucun"], ["Connaissances", agent.knowledge_scopes.join(", ")], ["Politique modèle", agent.model_policy.mode === "auto" ? "Automatique" : "Fixe"]];
  return <dl className="arc-agent-facts">{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Chargement du registre impossible.";
}
