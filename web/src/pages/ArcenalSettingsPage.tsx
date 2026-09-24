import { useCallback, useEffect, useState, type ChangeEvent, type Dispatch, type FormEvent, type ReactElement, type SetStateAction } from "react";
import { CheckCircle2, CircleAlert, ExternalLink, KeyRound, LoaderCircle, PlugZap, RefreshCw, ShieldCheck } from "lucide-react";
import { api, type ArcenalOpenRouterProbeResponse, type ModelAssignmentResponse } from "@/lib/api";
import { connectionLabel, openRouterModelSelection } from "@/lib/arcenal-openrouter";

interface OpenRouterSettingsState {
  apiKey: string;
  busy: boolean;
  configured: boolean;
  error: string;
  model: string;
  models: string[];
  notice: string;
  probe: ArcenalOpenRouterProbeResponse | null;
}

const INITIAL_STATE: OpenRouterSettingsState = {
  apiKey: "", busy: true, configured: false, error: "", model: "", models: [], notice: "", probe: null,
};

export default function ArcenalSettingsPage(): ReactElement {
  const [state, setState] = useState<OpenRouterSettingsState>(INITIAL_STATE);
  const load = useCallback(async (): Promise<void> => {
    try {
      const [variables, options, probe] = await Promise.all([
        api.getEnvVars(), api.getModelOptions(), api.testArcenalOpenRouter(),
      ]);
      const selection = openRouterModelSelection(options);
      setState((current) => ({ ...current, busy: false, configured: variables.OPENROUTER_API_KEY?.is_set === true, model: selection.current, models: selection.models, probe }));
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return <SettingsView state={state} setState={setState} reload={load} />;
}

function SettingsView({ state, setState, reload }: { state: OpenRouterSettingsState; setState: Dispatch<SetStateAction<OpenRouterSettingsState>>; reload: () => Promise<void> }): ReactElement {
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void connectOpenRouter(state, setState, reload);
  };
  return (
    <main className="arc-workspace arc-settings" aria-labelledby="settings-title">
      <SettingsHeading />
      {state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}
      {state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}
      <section className="arc-settings-grid">
        <OpenRouterForm state={state} setState={setState} onSubmit={submit} />
        <ConnectionSummary state={state} setState={setState} />
      </section>
    </main>
  );
}

function SettingsHeading(): ReactElement {
  return <header className="arc-workspace-heading"><p>Paramètres · Fournisseur IA</p><h1 id="settings-title">Connecter ARC à OpenRouter</h1><span>La clé reste dans l’espace privé de l’application YunoHost. Elle n’est jamais affichée après son enregistrement.</span></header>;
}

function OpenRouterForm({ state, setState, onSubmit }: { state: OpenRouterSettingsState; setState: Dispatch<SetStateAction<OpenRouterSettingsState>>; onSubmit: (event: FormEvent<HTMLFormElement>) => void }): ReactElement {
  return (
    <form className="arc-settings-card" onSubmit={onSubmit}>
      <div className="arc-settings-card-title"><span><KeyRound aria-hidden /></span><div><small>Identifiants</small><h2>Compte OpenRouter</h2></div></div>
      <PasswordField state={state} setState={setState} />
      <ModelField state={state} setState={setState} />
      <button className="arc-primary-button" disabled={state.busy || (!state.configured && !state.apiKey.trim()) || !state.model.trim()} type="submit">
        {state.busy ? <LoaderCircle className="arc-spin" aria-hidden /> : <PlugZap aria-hidden />}
        {state.configured ? "Enregistrer et reconnecter" : "Connecter OpenRouter"}
      </button>
      <small className="arc-settings-help">La modification s’applique aux nouvelles conversations ARC. La conversation en cours conserve son modèle jusqu’à son redémarrage.</small>
    </form>
  );
}

function PasswordField({ state, setState }: SettingsControlProps): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, apiKey: event.target.value, error: "", notice: "" }));
  return <label className="arc-field"><span>Clé API OpenRouter</span><input type="password" autoComplete="new-password" value={state.apiKey} placeholder={state.configured ? "Clé enregistrée — saisissez uniquement pour la remplacer" : "sk-or-v1-…"} onChange={change} /><small>Créez ou gérez vos clés sur <a href="https://openrouter.ai/settings/keys" target="_blank" rel="noreferrer">OpenRouter <ExternalLink aria-hidden /></a>.</small></label>;
}

function ModelField({ state, setState }: SettingsControlProps): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, model: event.target.value, error: "", notice: "" }));
  return <label className="arc-field"><span>Modèle principal d’ARC</span><input list="arc-openrouter-models" value={state.model} placeholder="Choisissez ou saisissez un modèle" onChange={change} /><datalist id="arc-openrouter-models">{state.models.map((model) => <option key={model} value={model} />)}</datalist><small>{state.models.length > 0 ? `${state.models.length} modèles OpenRouter disponibles.` : "Le catalogue sera disponible après la connexion."}</small></label>;
}

function ConnectionSummary({ state, setState }: SettingsControlProps): ReactElement {
  const test = (): void => { void testConnection(state.apiKey, setState); };
  return (
    <aside className="arc-settings-card arc-connection-card">
      <div className="arc-settings-card-title"><span><ShieldCheck aria-hidden /></span><div><small>Diagnostic</small><h2>État de la connexion</h2></div></div>
      <ConnectionBadge probe={state.probe} busy={state.busy} />
      <dl><div><dt>Clé</dt><dd>{state.configured ? "Enregistrée" : "À configurer"}</dd></div><div><dt>Fournisseur</dt><dd>OpenRouter</dd></div><div><dt>Modèle</dt><dd>{state.model || "À choisir"}</dd></div></dl>
      <p>{state.probe?.message ?? "Lancez le test pour vérifier l’accès sans exécuter de requête de génération."}</p>
      <button className="arc-secondary-button" disabled={state.busy || (!state.configured && !state.apiKey.trim())} onClick={test} type="button"><RefreshCw aria-hidden /> Tester la connexion</button>
    </aside>
  );
}

function ConnectionBadge({ probe, busy }: { probe: ArcenalOpenRouterProbeResponse | null; busy: boolean }): ReactElement {
  const connected = probe?.connection === "connected";
  return <div className="arc-connection-badge" data-status={probe?.connection ?? "unknown"}>{connected ? <CheckCircle2 aria-hidden /> : <CircleAlert aria-hidden />}<span><small>OpenRouter</small><strong>{busy ? "Vérification…" : connectionLabel(probe)}</strong></span></div>;
}

interface SettingsControlProps {
  setState: Dispatch<SetStateAction<OpenRouterSettingsState>>;
  state: OpenRouterSettingsState;
}

async function testConnection(apiKey: string, setState: SettingsControlProps["setState"]): Promise<ArcenalOpenRouterProbeResponse | null> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const probe = await api.testArcenalOpenRouter(apiKey || undefined);
    setState((current) => ({ ...current, busy: false, probe }));
    return probe;
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
    return null;
  }
}

async function connectOpenRouter(state: OpenRouterSettingsState, setState: SettingsControlProps["setState"], reload: () => Promise<void>): Promise<void> {
  try {
    const probe = await testConnection(state.apiKey, setState);
    if (!probe || probe.connection !== "connected") return;
    setState((current) => ({ ...current, busy: true }));
    if (state.apiKey.trim()) await api.setEnvVar("OPENROUTER_API_KEY", state.apiKey.trim());
    if (!(await assignOpenRouterModel(state.model.trim()))) {
      setState((current) => ({ ...current, busy: false, error: "Le modèle OpenRouter n’a pas été activé." }));
      return;
    }
    setState((current) => ({ ...current, apiKey: "", notice: "OpenRouter est connecté et devient le fournisseur principal d’ARC." }));
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function assignOpenRouterModel(model: string): Promise<boolean> {
  const response = await api.setModelAssignment({ scope: "main", provider: "openrouter", model });
  if (!response.confirm_required) return response.ok;
  if (!window.confirm(response.confirm_message ?? "Ce modèle peut entraîner un coût élevé. Continuer ?")) return false;
  const confirmed = await confirmModelAssignment(model);
  return confirmed.ok;
}

function confirmModelAssignment(model: string): Promise<ModelAssignmentResponse> {
  return api.setModelAssignment({ scope: "main", provider: "openrouter", model, confirm_expensive_model: true });
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "La connexion OpenRouter n’a pas pu être configurée.";
}
