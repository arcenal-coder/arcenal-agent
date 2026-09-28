import { useCallback, useEffect, useState, type ChangeEvent, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { Bot, CheckCircle2, KeyRound, LoaderCircle, Network, Plus, ShieldCheck } from "lucide-react";
import { api, type ArcenalProviderProbe, type EnvVarInfo, type ModelOptionsResponse } from "@/lib/api";
import { autonomyFromConfig, buildProviderConnections, normalizeCustomEnvKey, type AutonomyLevel, type ProviderConnection } from "@/lib/arcenal-providers";
import { ArcenalAccessManager } from "@/components/ArcenalAccessManager";
import { ArcenalCapabilitiesSettings } from "@/components/ArcenalCapabilitiesSettings";
import { ArcenalAppearanceSettingsPanel } from "@/components/ArcenalAppearanceSettings";
import { ArcenalGeneralSettingsPanel } from "@/components/ArcenalGeneralSettings";
import { ArcenalManagedFilesSettingsPanel } from "@/components/ArcenalManagedFilesSettings";
import { ArcenalMemorySettingsPanel } from "@/components/ArcenalMemorySettings";
import { isProviderStatusesResponse } from "@/lib/arcenal-provider-status";
import { ARCENAL_SETTINGS_TABS, type ArcenalSettingsTab } from "@/lib/arcenal-settings-tabs";

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
  enabledProviders: Record<string, boolean>;
  providerStatuses: Record<string, ArcenalProviderProbe>;
  providerUrls: Record<string, string>;
  secrets: Record<string, string>;
  selectedModels: Record<string, string>;
  selectedSecondaryModels: Record<string, string>;
}

const EMPTY_OPTIONS: ModelOptionsResponse = { providers: [] };
const INITIAL_STATE: SettingsState = { autonomy: "manual", busy: true, config: {}, customKey: "", customSecret: "", enabledProviders: {}, env: {}, error: "", models: EMPTY_OPTIONS, notice: "", providerStatuses: {}, providerUrls: {}, secrets: {}, selectedModels: {}, selectedSecondaryModels: {} };

export default function ArcenalSettingsPage(): ReactElement {
  const [state, setState] = useState<SettingsState>(INITIAL_STATE);
  const load = useCallback(async (): Promise<void> => {
    try {
      const [env, config, models, statuses] = await Promise.all([api.getEnvVars(), api.getConfig(), api.getModelOptions(), api.getArcenalProviderStatuses().catch(() => ({ providers: {} }))]);
      const providerStatuses = isProviderStatusesResponse(statuses) ? statuses.providers : {};
      setState((current) => loadedState(current, env, config, models, providerStatuses));
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return <SettingsView state={state} setState={setState} reload={load} />;
}

function loadedState(current: SettingsState, env: Record<string, EnvVarInfo>, config: Record<string, unknown>, models: ModelOptionsResponse, providerStatuses: Record<string, ArcenalProviderProbe>): SettingsState {
  const providers = config.providers as Record<string, { base_url?: string; enabled?: boolean }> | undefined;
  const connections = buildProviderConnections(env, providers);
  return { ...current, autonomy: autonomyFromConfig(config), busy: false, config, enabledProviders: Object.fromEntries(connections.map((item) => [item.id, item.enabled])), env, models, providerStatuses, providerUrls: Object.fromEntries(connections.map((item) => [item.id, providers?.[item.id]?.base_url || item.defaultBaseUrl])), selectedModels: modelDefaults(models) };
}

function modelDefaults(options: ModelOptionsResponse): Record<string, string> {
  return Object.fromEntries((options.providers ?? []).map((provider) => [provider.slug, provider.slug === options.provider ? options.model ?? provider.models?.[0] ?? "" : provider.models?.[0] ?? ""]));
}

function SettingsView({ state, setState, reload }: ViewProps): ReactElement {
  const [activeTab, setActiveTab] = useState<ArcenalSettingsTab>("general");
  const providers = state.config.providers as Record<string, { base_url?: unknown }> | undefined;
  const connections = buildProviderConnections(state.env, providers);
  return <main className="arc-workspace arc-settings" aria-labelledby="settings-title">
    <header className="arc-workspace-heading"><p>Paramètres · Intelligence et sécurité</p><h1 id="settings-title">Connexions et autonomie d’ARC</h1><span>Ajoutez plusieurs moteurs IA, choisissez leurs usages et gardez la maîtrise des actions d’administration.</span></header>
    {state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}
    {state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}
    <nav aria-label="Sections des paramètres" className="arc-settings-tabs">{ARCENAL_SETTINGS_TABS.map((tab) => <button aria-pressed={activeTab === tab.id} key={tab.id} onClick={() => setActiveTab(tab.id)} type="button">{tab.label}</button>)}</nav>
    {activeTab === "general" && <ArcenalGeneralSettingsPanel config={state.config} onReload={reload} />}
    {activeTab === "appearance" && <ArcenalAppearanceSettingsPanel config={state.config} onReload={reload} />}
    {activeTab === "context" && <ArcenalManagedFilesSettingsPanel category="context" key="context" />}
    {activeTab === "memory" && <ArcenalMemorySettingsPanel />}
    {activeTab === "directives" && <ArcenalManagedFilesSettingsPanel category="directive" key="directive" />}
    {activeTab === "providers" && <section className="arc-settings-section"><SectionTitle icon={<Network />} eyebrow="Moteurs IA" title="Connexions et API" description="Les connexions restent disponibles simultanément. Une clé enregistrée n’est jamais réaffichée." />
      <div className="arc-provider-grid">{connections.map((provider) => <ProviderCard key={provider.id} provider={provider} state={state} setState={setState} reload={reload} />)}</div>
      <CustomConnection state={state} setState={setState} reload={reload} />
    </section>}
    {activeTab === "access" && <ArcenalAccessManager config={state.config} env={state.env} reload={reload} />}
    {activeTab === "tools" && <ArcenalCapabilitiesSettings />}
    {activeTab === "security" && <AutonomySettings state={state} setState={setState} />}
  </main>;
}

function SectionTitle({ icon, eyebrow, title, description }: { icon: ReactElement; eyebrow: string; title: string; description: string }): ReactElement {
  return <div className="arc-settings-section-title"><span>{icon}</span><div><small>{eyebrow}</small><h2>{title}</h2><p>{description}</p></div></div>;
}

function ProviderCard({ provider, state, setState, reload }: ProviderProps): ReactElement {
  const discovered = state.providerStatuses[provider.id]?.models ?? [];
  const configured = state.models.providers?.find((item) => item.slug === provider.id)?.models ?? [];
  const models = [...new Set([...configured, ...discovered])];
  const secret = state.secrets[provider.id] ?? "";
  const save = (): void => { void saveProvider(provider, state, setState, reload); };
  const test = (): void => { void testProvider(provider, state, setState); };
  const status = state.providerStatuses[provider.id];
  return <article className="arc-provider-card" data-configured={provider.configured}>
    <header><span><Bot aria-hidden /></span><div><h3>{provider.label}</h3><small>{provider.local ? "Moteur local ou privé" : "Service externe"}</small></div><em data-state={status?.connection}>{provider.configured ? <><CheckCircle2 /> Configuré</> : "À connecter"}</em></header>
    {provider.configurableUrl && <ProviderUrlInput provider={provider} state={state} setState={setState} />}
    {provider.keyRequired && <SecretInput provider={provider} value={secret} setState={setState} />}
    <ModelSelect label="Modèle principal" provider={provider} models={models} state={state} setState={setState} />
    <ModelSelect label="Modèle secondaire" provider={provider} models={models} secondary state={state} setState={setState} />
    <label className="arc-provider-toggle"><input checked={state.enabledProviders[provider.id] !== false} onChange={(event) => setState((current) => ({ ...current, enabledProviders: { ...current.enabledProviders, [provider.id]: event.target.checked } }))} type="checkbox" /><span>Connexion active</span></label>
    {status && <p className="arc-provider-status" data-state={status.connection}>{status.message}<small>Dernier test : {formatTestDate(status.tested_at)}</small></p>}
    <div className="arc-provider-actions"><button disabled={state.busy} onClick={test} type="button">Tester la connexion</button><button className="arc-primary-button" disabled={state.busy || (provider.keyRequired && !provider.configured && !secret.trim())} onClick={save} type="button">{state.busy ? <LoaderCircle className="arc-spin" /> : <KeyRound />} {provider.configured ? "Mettre à jour" : "Connecter"}</button></div>
  </article>;
}

function SecretInput({ provider, value, setState }: { provider: ProviderConnection; value: string; setState: SetState }): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, secrets: { ...current.secrets, [provider.id]: event.target.value } }));
  return <label className="arc-field"><span>Clé API</span><input autoComplete="new-password" onChange={change} placeholder={provider.configured ? "Clé enregistrée — saisir pour remplacer" : "Coller la clé API"} type="password" value={value} /></label>;
}

function ProviderUrlInput({ provider, state, setState }: { provider: ProviderConnection; state: SettingsState; setState: SetState }): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, providerUrls: { ...current.providerUrls, [provider.id]: event.target.value } }));
  return <label className="arc-field"><span>Adresse du service</span><input onChange={change} placeholder={provider.defaultBaseUrl || "https://llm.interne/v1"} type="url" value={state.providerUrls[provider.id] ?? ""} /><small>Indiquez la racine compatible OpenAI, sans identifiants dans l’URL.</small></label>;
}

function ModelSelect({ label, provider, models, secondary = false, state, setState }: { label: string; provider: ProviderConnection; models: string[]; secondary?: boolean; state: SettingsState; setState: SetState }): ReactElement {
  const collection = secondary ? state.selectedSecondaryModels : state.selectedModels;
  const value = collection[provider.id] ?? "";
  const change = (event: ChangeEvent<HTMLInputElement>): void => patchSelectedModel(provider.id, event.target.value, secondary, setState);
  return <label className="arc-field"><span>{label}</span><input list={`models-${provider.id}`} onChange={change} placeholder={provider.local ? "ex. qwen3:8b" : "Choisir ou saisir un modèle"} value={value} /><datalist id={`models-${provider.id}`}>{models.map((model) => <option key={model} value={model} />)}</datalist></label>;
}

async function saveProvider(provider: ProviderConnection, state: SettingsState, setState: SetState, reload: () => Promise<void>): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const secret = state.secrets[provider.id]?.trim();
    if (provider.envKey && secret) await api.setEnvVar(provider.envKey, secret);
    const baseUrl = state.providerUrls[provider.id]?.trim();
    await api.saveConfig({ providers: { [provider.id]: { base_url: baseUrl || undefined, enabled: state.enabledProviders[provider.id] !== false } } });
    const runtimeProvider = provider.id === "compatible" || provider.id === "internal" ? "custom" : provider.id;
    const model = state.selectedModels[provider.id]?.trim();
    if (model) await activateModel("main", runtimeProvider, model, baseUrl);
    const secondary = state.selectedSecondaryModels[provider.id]?.trim();
    if (secondary) await activateModel("auxiliary", runtimeProvider, secondary, baseUrl);
    setState((current) => ({ ...current, notice: `${provider.label} est disponible pour ARC.`, secrets: { ...current.secrets, [provider.id]: "" } }));
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

async function activateModel(scope: "main" | "auxiliary", provider: string, model: string, baseUrl = ""): Promise<void> {
  const request = { scope, provider, model, base_url: baseUrl || undefined, task: scope === "auxiliary" ? "" : undefined } as const;
  const response = await api.setModelAssignment(request);
  if (!response.confirm_required) return;
  if (!window.confirm(response.confirm_message ?? "Ce modèle peut entraîner un coût. Continuer ?")) return;
  await api.setModelAssignment({ ...request, confirm_expensive_model: true });
}

async function testProvider(provider: ProviderConnection, state: SettingsState, setState: SetState): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const status = await api.testArcenalProvider(provider.id, state.secrets[provider.id], state.providerUrls[provider.id]);
    if (!isProviderStatusesResponse({ providers: { [provider.id]: status } })) throw new Error("La réponse du fournisseur est incomplète.");
    setState((current) => ({ ...current, busy: false, providerStatuses: { ...current.providerStatuses, [provider.id]: status } }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
}

function patchSelectedModel(providerId: string, value: string, secondary: boolean, setState: SetState): void {
  if (secondary) {
    setState((current) => ({ ...current, selectedSecondaryModels: { ...current.selectedSecondaryModels, [providerId]: value } }));
    return;
  }
  setState((current) => ({ ...current, selectedModels: { ...current.selectedModels, [providerId]: value } }));
}

function formatTestDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "date inconnue" : date.toLocaleString("fr-FR");
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
    { id: "off", title: "Administration contrôlée", text: "ARC applique les politiques définies. Les actions critiques exigent toujours votre confirmation." },
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
