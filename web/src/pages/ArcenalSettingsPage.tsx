import { useCallback, useEffect, useState, type ChangeEvent, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { Bot, CheckCircle2, KeyRound, LoaderCircle, Monitor, Moon, Network, Plus, ShieldCheck, Sun } from "lucide-react";
import { api, type EnvVarInfo, type ModelOptionsResponse } from "@/lib/api";
import { autonomyFromConfig, buildProviderConnections, normalizeCustomEnvKey, type AutonomyLevel, type ProviderConnection } from "@/lib/arcenal-providers";
import { ArcenalAccessManager } from "@/components/ArcenalAccessManager";
import { useArcColorMode, type ArcColorMode } from "@/lib/arcenal-color-mode";

interface SettingsState {
  autonomy: AutonomyLevel;
  busy: boolean;
  config: Record<string, unknown>;
  customKey: string;
  customSecret: string;
  env: Record<string, EnvVarInfo>;
  error: string;
  models: ModelOptionsResponse;
  notice: string;
  ollamaUrl: string;
  secrets: Record<string, string>;
  selectedModels: Record<string, string>;
}

const EMPTY_OPTIONS: ModelOptionsResponse = { providers: [] };
const INITIAL_STATE: SettingsState = { autonomy: "manual", busy: true, config: {}, customKey: "", customSecret: "", env: {}, error: "", models: EMPTY_OPTIONS, notice: "", ollamaUrl: "http://127.0.0.1:11434/v1", secrets: {}, selectedModels: {} };

export default function ArcenalSettingsPage(): ReactElement {
  const [state, setState] = useState<SettingsState>(INITIAL_STATE);
  const load = useCallback(async (): Promise<void> => {
    try {
      const [env, config, models] = await Promise.all([api.getEnvVars(), api.getConfig(), api.getModelOptions()]);
      setState((current) => loadedState(current, env, config, models));
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return <SettingsView state={state} setState={setState} reload={load} />;
}

function loadedState(current: SettingsState, env: Record<string, EnvVarInfo>, config: Record<string, unknown>, models: ModelOptionsResponse): SettingsState {
  const providers = config.providers as Record<string, { base_url?: string }> | undefined;
  return { ...current, autonomy: autonomyFromConfig(config), busy: false, config, env, models, ollamaUrl: providers?.ollama?.base_url || current.ollamaUrl, selectedModels: modelDefaults(models) };
}

function modelDefaults(options: ModelOptionsResponse): Record<string, string> {
  return Object.fromEntries((options.providers ?? []).map((provider) => [provider.slug, provider.slug === options.provider ? options.model ?? provider.models?.[0] ?? "" : provider.models?.[0] ?? ""]));
}

function SettingsView({ state, setState, reload }: ViewProps): ReactElement {
  const providers = state.config.providers as Record<string, { base_url?: unknown }> | undefined;
  const connections = buildProviderConnections(state.env, providers);
  return <main className="arc-workspace arc-settings" aria-labelledby="settings-title">
    <header className="arc-workspace-heading"><p>Paramètres · Intelligence et sécurité</p><h1 id="settings-title">Connexions et autonomie d’ARC</h1><span>Ajoutez plusieurs moteurs IA, choisissez leurs usages et gardez la maîtrise des actions d’administration.</span></header>
    {state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}
    {state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}
    <AppearanceSettings />
    <section className="arc-settings-section"><SectionTitle icon={<Network />} eyebrow="Moteurs IA" title="Connexions et API" description="Les connexions restent disponibles simultanément. Une clé enregistrée n’est jamais réaffichée." />
      <div className="arc-provider-grid">{connections.map((provider) => <ProviderCard key={provider.id} provider={provider} state={state} setState={setState} reload={reload} />)}</div>
      <CustomConnection state={state} setState={setState} reload={reload} />
    </section>
    <ArcenalAccessManager config={state.config} env={state.env} reload={reload} />
    <AutonomySettings state={state} setState={setState} />
  </main>;
}

function AppearanceSettings(): ReactElement {
  const { mode, setMode } = useArcColorMode();
  const options: Array<{ icon: ReactElement; id: ArcColorMode; label: string }> = [{ icon: <Sun />, id: "light", label: "Clair" }, { icon: <Moon />, id: "dark", label: "Sombre" }, { icon: <Monitor />, id: "system", label: "Système" }];
  return <section className="arc-appearance" aria-label="Apparence"><strong>Thème</strong><div>{options.map((option) => <button aria-pressed={mode === option.id} key={option.id} onClick={() => setMode(option.id)} type="button">{option.icon}<span>{option.label}</span></button>)}</div></section>;
}

function SectionTitle({ icon, eyebrow, title, description }: { icon: ReactElement; eyebrow: string; title: string; description: string }): ReactElement {
  return <div className="arc-settings-section-title"><span>{icon}</span><div><small>{eyebrow}</small><h2>{title}</h2><p>{description}</p></div></div>;
}

function ProviderCard({ provider, state, setState, reload }: ProviderProps): ReactElement {
  const models = state.models.providers?.find((item) => item.slug === provider.id)?.models ?? [];
  const secret = state.secrets[provider.id] ?? "";
  const save = (): void => { void saveProvider(provider, state, setState, reload); };
  return <article className="arc-provider-card" data-configured={provider.configured}>
    <header><span><Bot aria-hidden /></span><div><h3>{provider.label}</h3><small>{provider.local ? "Moteur local" : "Service externe"}</small></div><em>{provider.configured ? <><CheckCircle2 /> Configuré</> : "À connecter"}</em></header>
    {provider.keyRequired ? <SecretInput provider={provider} value={secret} setState={setState} /> : <OllamaInput state={state} setState={setState} />}
    <ModelSelect provider={provider} models={models} state={state} setState={setState} />
    <button className="arc-primary-button" disabled={state.busy || (provider.keyRequired && !provider.configured && !secret.trim())} onClick={save} type="button">{state.busy ? <LoaderCircle className="arc-spin" /> : <KeyRound />} {provider.configured ? "Mettre à jour" : "Connecter"}</button>
  </article>;
}

function SecretInput({ provider, value, setState }: { provider: ProviderConnection; value: string; setState: SetState }): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, secrets: { ...current.secrets, [provider.id]: event.target.value } }));
  return <label className="arc-field"><span>Clé API</span><input autoComplete="new-password" onChange={change} placeholder={provider.configured ? "Clé enregistrée — saisir pour remplacer" : "Coller la clé API"} type="password" value={value} /></label>;
}

function OllamaInput({ state, setState }: { state: SettingsState; setState: SetState }): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, ollamaUrl: event.target.value }));
  return <label className="arc-field"><span>Adresse Ollama</span><input onChange={change} placeholder="http://127.0.0.1:11434/v1" type="url" value={state.ollamaUrl} /><small>Ollama peut fonctionner sur ce serveur ou sur une machine du réseau.</small></label>;
}

function ModelSelect({ provider, models, state, setState }: { provider: ProviderConnection; models: string[]; state: SettingsState; setState: SetState }): ReactElement {
  const value = state.selectedModels[provider.id] ?? "";
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, selectedModels: { ...current.selectedModels, [provider.id]: event.target.value } }));
  return <label className="arc-field"><span>Modèle à activer</span><input list={`models-${provider.id}`} onChange={change} placeholder={provider.local ? "ex. qwen3:8b" : "Choisir ou saisir un modèle"} value={value} /><datalist id={`models-${provider.id}`}>{models.map((model) => <option key={model} value={model} />)}</datalist></label>;
}

async function saveProvider(provider: ProviderConnection, state: SettingsState, setState: SetState, reload: () => Promise<void>): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const secret = state.secrets[provider.id]?.trim();
    if (provider.envKey && secret) await api.setEnvVar(provider.envKey, secret);
    if (provider.id === "ollama") await api.saveConfig({ providers: { ollama: { base_url: state.ollamaUrl.trim() } } });
    const model = state.selectedModels[provider.id]?.trim();
    if (model) await activateModel(provider.id, model);
    setState((current) => ({ ...current, notice: `${provider.label} est disponible pour ARC.`, secrets: { ...current.secrets, [provider.id]: "" } }));
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function activateModel(provider: string, model: string): Promise<void> {
  const response = await api.setModelAssignment({ scope: "main", provider, model });
  if (!response.confirm_required) return;
  if (!window.confirm(response.confirm_message ?? "Ce modèle peut entraîner un coût. Continuer ?")) return;
  await api.setModelAssignment({ scope: "main", provider, model, confirm_expensive_model: true });
}

function CustomConnection({ state, setState, reload }: ViewProps): ReactElement {
  const save = (): void => { void saveCustomConnection(state, setState, reload); };
  return <article className="arc-custom-connection"><div><Plus aria-hidden /><span><strong>Compte ou API personnalisé</strong><small>Ajoutez un jeton utilisable par un outil, un connecteur ou un futur fournisseur.</small></span></div><input aria-label="Nom de la variable" onChange={(event) => setState((current) => ({ ...current, customKey: event.target.value }))} placeholder="NOM_DU_SERVICE_API_KEY" value={state.customKey} /><input aria-label="Secret" autoComplete="new-password" onChange={(event) => setState((current) => ({ ...current, customSecret: event.target.value }))} placeholder="Clé ou jeton" type="password" value={state.customSecret} /><button disabled={state.busy || !state.customKey.trim() || !state.customSecret.trim()} onClick={save} type="button">Ajouter</button></article>;
}

async function saveCustomConnection(state: SettingsState, setState: SetState, reload: () => Promise<void>): Promise<void> {
  const key = normalizeCustomEnvKey(state.customKey);
  if (!key) { setState((current) => ({ ...current, error: "Le nom de cette connexion n’est pas autorisé." })); return; }
  try {
    setState((current) => ({ ...current, busy: true, error: "" }));
    await api.setEnvVar(key, state.customSecret.trim());
    setState((current) => ({ ...current, customKey: "", customSecret: "", notice: "La connexion personnalisée est enregistrée." }));
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

function AutonomySettings({ state, setState }: { state: SettingsState; setState: SetState }): ReactElement {
  const levels: Array<{ id: AutonomyLevel; title: string; text: string }> = [
    { id: "manual", title: "Validation systématique", text: "ARC conseille et demande votre accord avant chaque commande sensible." },
    { id: "smart", title: "Autonomie encadrée", text: "ARC exécute les actions sûres et sollicite l’administrateur en cas de risque." },
    { id: "off", title: "Autonomie étendue", text: "ARC peut exécuter les actions administratives sans validation préalable." },
  ];
  const save = (): void => { void saveAutonomy(state.autonomy, setState); };
  return <section className="arc-settings-section"><SectionTitle icon={<ShieldCheck />} eyebrow="Sécurité" title="Niveau d’autonomie" description="Ce réglage contrôle les validations demandées avant les commandes d’administration." /><div className="arc-autonomy-grid">{levels.map((level) => <label key={level.id} data-selected={state.autonomy === level.id}><input checked={state.autonomy === level.id} name="autonomy" onChange={() => setState((current) => ({ ...current, autonomy: level.id }))} type="radio" /><span><strong>{level.title}</strong><small>{level.text}</small></span></label>)}</div><button className="arc-primary-button arc-save-autonomy" disabled={state.busy} onClick={save} type="button">Enregistrer le niveau d’autonomie</button></section>;
}

async function saveAutonomy(level: AutonomyLevel, setState: SetState): Promise<void> {
  try {
    setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
    await api.saveConfig({ approvals: { mode: level } });
    setState((current) => ({ ...current, busy: false, notice: "Le niveau d’autonomie d’ARC est enregistré." }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

type SetState = Dispatch<SetStateAction<SettingsState>>;
interface ViewProps { reload: () => Promise<void>; setState: SetState; state: SettingsState }
interface ProviderProps extends ViewProps { provider: ProviderConnection }

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Les paramètres n’ont pas pu être enregistrés.";
}
