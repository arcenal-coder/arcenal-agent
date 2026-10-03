import { useCallback, useEffect, useState, type FormEvent, type ReactElement } from "react";
import { Bot, Plus, X } from "lucide-react";
import { api, type ArcenalModelDescriptor } from "@/lib/api";
import { buildAgentModelPolicy, createManagedAgent, loadManagedAgents, modelsForAgent, modelsForPrivacy, modelsForProvider, requiredAgentPrivacy, updateManagedAgent, type AgentAutonomy, type AgentHarness, type AgentModelMode, type ManagedAgent, type ManagedAgentUpdate } from "@/lib/arcenal-agent-manager";

const AUTONOMY_LABELS: Record<AgentAutonomy, string> = {
  approval_required: "Validation requise",
  automatic: "Automatique",
  controlled: "Contrôlée",
};

export function ArcenalCoreAgentsPanel(): ReactElement {
  const state = useManagedAgents();
  return (
    <section className="arc-agent-main arc-core-agents">
      <PanelHeading count={state.agents.length} onCreate={() => state.setCreating(true)} />
      {state.error && <p className="arc-alert arc-alert-error">{state.error}</p>}
      <div className="arc-agent-grid">
        {state.agents.map((agent) => <ManagedAgentCard agent={agent} key={agent.id} onOpen={state.setSelected} />)}
      </div>
      {state.selected && <ManagedAgentDialog agent={state.selected} models={state.models} onClose={() => state.setSelected(null)} onSave={state.save} />}
      {state.creating && <ManagedAgentCreateDialog models={state.models} onClose={() => state.setCreating(false)} onCreate={state.create} />}
    </section>
  );
}

function useManagedAgents(): ManagedAgentsState {
  const [agents, setAgents] = useState<ManagedAgent[]>([]);
  const [models, setModels] = useState<ArcenalModelDescriptor[]>([]);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<ManagedAgent | null>(null);
  const [error, setError] = useState("");
  const load = useCallback((): Promise<void> => refreshAgents(setAgents, setModels, setError), []);
  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);
  const save = (update: ManagedAgentUpdate): Promise<void> => persistAgent(selected, update, setSelected, load, setError);
  const create = (agent: ManagedAgent): Promise<void> => persistNewAgent(agent, setCreating, load, setError);
  return { agents, create, creating, error, models, save, selected, setCreating, setSelected };
}

interface ManagedAgentsState {
  agents: ManagedAgent[];
  create: (agent: ManagedAgent) => Promise<void>;
  creating: boolean;
  error: string;
  models: ArcenalModelDescriptor[];
  save: (update: ManagedAgentUpdate) => Promise<void>;
  selected: ManagedAgent | null;
  setCreating: (value: boolean) => void;
  setSelected: (agent: ManagedAgent | null) => void;
}

async function refreshAgents(setAgents: (agents: ManagedAgent[]) => void, setModels: (models: ArcenalModelDescriptor[]) => void, setError: (error: string) => void): Promise<void> {
  try {
    const [agents, overview] = await Promise.all([loadManagedAgents(), api.getArcenalFrugalOverview()]);
    setAgents(agents);
    setModels(overview.models);
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

async function persistNewAgent(agent: ManagedAgent, setCreating: (value: boolean) => void, reload: () => Promise<void>, setError: (error: string) => void): Promise<void> {
  try {
    await createManagedAgent(agent);
    setCreating(false);
    await reload();
  } catch (cause) {
    setError(errorMessage(cause));
  }
}

function PanelHeading({ count, onCreate }: { count: number; onCreate: () => void }): ReactElement {
  return (
    <div className="arc-panel-heading">
      <div><span>ARC Core · Agent Manager</span><h2>{count} agent{count === 1 ? "" : "s"} gouverné{count === 1 ? "" : "s"}</h2></div>
      <button className="arc-primary-button" onClick={onCreate} type="button"><Plus aria-hidden />Créer un agent gouverné</button>
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

function ManagedAgentDialog({ agent, models, onClose, onSave }: { agent: ManagedAgent; models: ArcenalModelDescriptor[]; onClose: () => void; onSave: (update: ManagedAgentUpdate) => Promise<void> }): ReactElement {
  return (
    <div className="arc-agent-modal" role="dialog" aria-modal="true" aria-labelledby="core-agent-title">
      <section>
        <header><div><span>{agent.id} · {agent.application}</span><h2 id="core-agent-title">{agent.name}</h2></div><button type="button" onClick={onClose} aria-label="Fermer"><X aria-hidden /></button></header>
        <p>{agent.description}</p>
        <AgentFacts agent={agent} />
        <label className="arc-agent-setting">Autonomie<select value={agent.autonomy_level} onChange={(event) => void onSave({ autonomy_level: event.target.value as AgentAutonomy })}>{Object.entries(AUTONOMY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="arc-agent-setting"><input checked={agent.enabled} type="checkbox" onChange={(event) => void onSave({ enabled: event.target.checked })} /> Agent activé</label>
        <AgentModelPolicyEditor agent={agent} models={models} onSave={onSave} />
        <AgentHarnessEditor harness={agent.harness} onSave={(harness) => onSave({ harness })} />
      </section>
    </div>
  );
}

function AgentHarnessEditor({ harness, onSave }: { harness: AgentHarness; onSave: (harness: AgentHarness) => Promise<void> }): ReactElement {
  const [draft, setDraft] = useState(harness);
  const update = (field: keyof AgentHarness, value: string): void => setDraft((current) => ({ ...current, [field]: value }));
  return <fieldset className="arc-agent-policy"><legend>Harnais de l’agent</legend><HarnessFields harness={draft} update={update} /><button onClick={() => void onSave(draft)} type="button">Enregistrer le harnais</button></fieldset>;
}

function HarnessFields({ harness, update }: { harness: AgentHarness; update: (field: keyof AgentHarness, value: string) => void }): ReactElement {
  return <><label>Contexte<textarea rows={5} value={harness.context} onChange={(event) => update("context", event.target.value)} /></label><label>Directives<textarea rows={6} value={harness.directives} onChange={(event) => update("directives", event.target.value)} /></label><label>Mémoire propre<textarea rows={6} value={harness.memory} onChange={(event) => update("memory", event.target.value)} /></label></>;
}

function AgentModelPolicyEditor({ agent, models, onSave }: { agent: ManagedAgent; models: ArcenalModelDescriptor[]; onSave: (update: ManagedAgentUpdate) => Promise<void> }): ReactElement {
  const compatibleModels = modelsForAgent(models, agent);
  const [mode, setMode] = useState<AgentModelMode>(agent.model_policy.mode);
  const [provider, setProvider] = useState(agent.model_policy.allowed_providers[0] || compatibleModels[0]?.provider || "");
  const [modelId, setModelId] = useState(agent.model_policy.allowed_models[0] || "");
  const [localOnly, setLocalOnly] = useState(agent.model_policy.local_only);
  const [localPreferred, setLocalPreferred] = useState(agent.model_policy.local_preferred);
  const available = localOnly ? compatibleModels.filter((model) => model.location === "local") : compatibleModels;
  const choices = modelsForProvider(available, provider);
  const providers = [...new Set(available.filter((model) => model.enabled && model.availability !== "unavailable").map((model) => model.provider))];
  const canSave = mode === "auto" || choices.some((model) => model.id === modelId);
  const save = (): void => void onSave({ model_policy: buildAgentModelPolicy(mode, provider, modelId, localOnly, localPreferred, models, agent.model_policy) });
  return <fieldset className="arc-agent-policy"><legend>Modèle de l’agent</legend><p>Confidentialité minimale requise : {requiredAgentPrivacy(agent)}. Les autres modèles sont exclus du sélecteur.</p><label>Mode<select value={mode} onChange={(event) => setMode(event.target.value as AgentModelMode)}><option value="auto">AUTO — routage ARC</option><option value="fixed">FIXED — modèle imposé</option></select></label>{mode === "fixed" && <FixedModelFields choices={choices} modelId={modelId} provider={provider} providers={providers} setModelId={setModelId} setProvider={setProvider} />}<label><input checked={localPreferred} onChange={(event) => setLocalPreferred(event.target.checked)} type="checkbox" /> Préférer un modèle local</label><label><input checked={localOnly} onChange={(event) => setLocalOnly(event.target.checked)} type="checkbox" /> Modèles locaux uniquement</label><button disabled={!canSave} onClick={save} type="button">Enregistrer la politique modèle</button></fieldset>;
}

function FixedModelFields({ choices, modelId, provider, providers, setModelId, setProvider }: { choices: ArcenalModelDescriptor[]; modelId: string; provider: string; providers: string[]; setModelId: (value: string) => void; setProvider: (value: string) => void }): ReactElement {
  const changeProvider = (value: string): void => { setProvider(value); setModelId(""); };
  return <><label>Fournisseur<select value={provider} onChange={(event) => changeProvider(event.target.value)}><option value="">Sélectionner</option>{providers.map((value) => <option key={value} value={value}>{value}</option>)}</select></label><label>Modèle<select value={modelId} onChange={(event) => setModelId(event.target.value)}><option value="">Sélectionner</option>{choices.map((model) => <option key={model.id} value={model.id}>{model.display_name || model.model_name}</option>)}</select></label></>;
}

function ManagedAgentCreateDialog({ models, onClose, onCreate }: { models: ArcenalModelDescriptor[]; onClose: () => void; onCreate: (agent: ManagedAgent) => Promise<void> }): ReactElement {
  const compatibleModels = modelsForPrivacy(models, "internal");
  const [identity, setIdentity] = useState({ application: "arcenal-system", description: "", id: "", name: "", role: "specialist", scopes: "company" });
  const [harness, setHarness] = useState<AgentHarness>({ context: "", directives: "", memory: "" });
  const [mode, setMode] = useState<AgentModelMode>("auto");
  const [provider, setProvider] = useState(compatibleModels[0]?.provider || "");
  const [modelId, setModelId] = useState("");
  const selectable = modelsForProvider(compatibleModels, provider);
  const providers = [...new Set(compatibleModels.filter((model) => model.enabled && model.availability !== "unavailable").map((model) => model.provider))];
  const validPolicy = mode === "auto" || selectable.some((model) => model.id === modelId);
  const change = (field: keyof typeof identity, value: string): void => setIdentity((current) => ({ ...current, [field]: value }));
  const submit = (event: FormEvent<HTMLFormElement>): void => { event.preventDefault(); void onCreate(createAgentDefinition(identity, harness, buildAgentModelPolicy(mode, provider, modelId, false, true, compatibleModels))); };
  const updateHarness = (field: keyof AgentHarness, value: string): void => setHarness((current) => ({ ...current, [field]: value }));
  return <div className="arc-agent-modal" role="dialog" aria-modal="true" aria-labelledby="create-core-agent-title"><section><header><div><span>ARC Core</span><h2 id="create-core-agent-title">Créer un agent gouverné</h2></div><button type="button" onClick={onClose} aria-label="Fermer"><X aria-hidden /></button></header><form className="arc-agent-policy" onSubmit={submit}><CreateIdentityFields identity={identity} change={change} /><label>Mode modèle<select value={mode} onChange={(event) => setMode(event.target.value as AgentModelMode)}><option value="auto">AUTO — routage propre à l’agent</option><option value="fixed">FIXED — modèle imposé</option></select></label>{mode === "fixed" && <FixedModelFields choices={selectable} modelId={modelId} provider={provider} providers={providers} setModelId={setModelId} setProvider={setProvider} />}<HarnessFields harness={harness} update={updateHarness} /><button disabled={!validPolicy} type="submit">Créer l’agent</button></form></section></div>;
}

type AgentIdentityDraft = { application: string; description: string; id: string; name: string; role: string; scopes: string };

function CreateIdentityFields({ identity, change }: { identity: AgentIdentityDraft; change: (field: keyof AgentIdentityDraft, value: string) => void }): ReactElement {
  return <><label>Identifiant<input pattern="[a-z0-9][a-z0-9-]{0,63}" required value={identity.id} onChange={(event) => change("id", event.target.value)} /></label><label>Nom<input required value={identity.name} onChange={(event) => change("name", event.target.value)} /></label><label>Description<input required value={identity.description} onChange={(event) => change("description", event.target.value)} /></label><label>Rôle<input required value={identity.role} onChange={(event) => change("role", event.target.value)} /></label><label>Application<input pattern="[a-z0-9][a-z0-9-]{0,63}" required value={identity.application} onChange={(event) => change("application", event.target.value)} /></label><label>Portées RAG<input required value={identity.scopes} onChange={(event) => change("scopes", event.target.value)} /></label></>;
}

function createAgentDefinition(identity: AgentIdentityDraft, harness: AgentHarness, modelPolicy: ManagedAgent["model_policy"]): ManagedAgent {
  const scopes = identity.scopes.split(",").map((value) => value.trim()).filter(Boolean);
  return { application: identity.application, autonomy_level: "controlled", description: identity.description, enabled: true, harness, id: identity.id, knowledge_scopes: scopes, metadata: {}, model_policy: modelPolicy, name: identity.name, permissions: [], role: identity.role, system_instructions: [{ content: identity.description, id: "mission" }], tools: [] };
}

function AgentFacts({ agent }: { agent: ManagedAgent }): ReactElement {
  const facts = [["Rôle", agent.role], ["Permissions", agent.permissions.join(", ") || "Aucune"], ["Outils", agent.tools.join(", ") || "Aucun"], ["Connaissances", agent.knowledge_scopes.join(", ")], ["Politique modèle", agent.model_policy.mode === "auto" ? "Automatique" : "Fixe"]];
  return <dl className="arc-agent-facts">{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Chargement du registre impossible.";
}
