import { useCallback, useEffect, useState, type ChangeEvent, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { Bot, CheckCircle2, KeyRound, LoaderCircle, Network, Plus, ShieldCheck } from "lucide-react";
import { api, type ArcenalProviderProbe, type ModelOptionsResponse, type OAuthProvider } from "@/lib/api";
import { autonomyFromConfig, buildProviderConnections, normalizeCustomEnvKey, type AutonomyLevel, type ProviderConnection } from "@/lib/arcenal-providers";
import { ArcenalAccessManager } from "@/components/ArcenalAccessManager";
import { ArcenalCapabilitiesSettings } from "@/components/ArcenalCapabilitiesSettings";
import { ArcenalAppearanceSettingsPanel } from "@/components/ArcenalAppearanceSettings";
import { ArcenalGeneralSettingsPanel } from "@/components/ArcenalGeneralSettings";
import { ArcenalFrugalSettingsPanel } from "@/components/ArcenalFrugalSettings";
import { ArcenalBackupSettingsPanel, ArcenalSystemSettingsPanel } from "@/components/ArcenalSystemSettings";
import { ArcenalSecuritySettingsPanel } from "@/components/ArcenalSecuritySettings";
import { isProviderStatusesResponse } from "@/lib/arcenal-provider-status";
import { ARCENAL_SETTINGS_TABS, type ArcenalSettingsTab } from "@/lib/arcenal-settings-tabs";
import { OAuthLoginModal } from "@/components/OAuthLoginModal";

interface SettingsState {
  autonomy: AutonomyLevel;
  busy: boolean;
  config: Record<string, unknown>;
  customKey: string;
  customSecret: string;
  env: Record<string, { is_set: boolean }>;
  error: string;
  models: ModelOptionsResponse;
  notice: string;
  enabledProviders: Record<string, boolean>;
  providerStatuses: Record<string, ArcenalProviderProbe>;
  providerUrls: Record<string, string>;
  secrets: Record<string, string>;
}

const EMPTY_OPTIONS: ModelOptionsResponse = { providers: [] };
const INITIAL_STATE: SettingsState = { autonomy: "manual", busy: true, config: {}, customKey: "", customSecret: "", enabledProviders: {}, env: {}, error: "", models: EMPTY_OPTIONS, notice: "", providerStatuses: {}, providerUrls: {}, secrets: {} };

export default function ArcenalSettingsPage(): ReactElement {
  const [state, setState] = useState<SettingsState>(INITIAL_STATE);
  const load = useCallback(async (): Promise<void> => {
    try {
      const [native, models, statuses] = await Promise.all([api.getArcenalConfiguration(), api.getModelOptions(), api.getArcenalProviderStatuses().catch(() => ({ providers: {} }))]);
      const providerStatuses = isProviderStatusesResponse(statuses) ? statuses.providers : {};
      setState((current) => loadedState(current, secretStates(native.secrets), native.config, models, providerStatuses));
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return <SettingsView state={state} setState={setState} reload={load} />;
}

function loadedState(current: SettingsState, env: Record<string, { is_set: boolean }>, config: Record<string, unknown>, models: ModelOptionsResponse, providerStatuses: Record<string, ArcenalProviderProbe>): SettingsState {
  const providers = config.providers as Record<string, { base_url?: string; enabled?: boolean }> | undefined;
  const connections = buildProviderConnections(env, providers);
  return { ...current, autonomy: autonomyFromConfig(config), busy: false, config, enabledProviders: Object.fromEntries(connections.map((item) => [item.id, item.enabled])), env, models, providerStatuses, providerUrls: Object.fromEntries(connections.map((item) => [item.id, providers?.[item.id]?.base_url || item.defaultBaseUrl])) };
}

function secretStates(values: Record<string, boolean>): Record<string, { is_set: boolean }> {
  return Object.fromEntries(Object.entries(values).map(([key, configured]) => [key, { is_set: configured }]));
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
    {activeTab === "providers" && <section className="arc-settings-section"><SectionTitle icon={<Network />} eyebrow="Moteurs IA" title="Connexions et API" description="Les connexions restent disponibles simultanément. Une clé enregistrée n’est jamais réaffichée." />
      <div className="arc-provider-grid"><CodexProviderCard state={state} setState={setState} reload={reload} />{connections.map((provider) => <ProviderCard key={provider.id} provider={provider} state={state} setState={setState} reload={reload} />)}</div>
      <CustomConnection state={state} setState={setState} reload={reload} />
    </section>}
    {activeTab === "frugal" && <ArcenalFrugalSettingsPanel />}
    {activeTab === "access" && <ArcenalAccessManager config={state.config} env={state.env} reload={reload} />}
    {activeTab === "tools" && <ArcenalCapabilitiesSettings />}
    {activeTab === "system" && <ArcenalSystemSettingsPanel />}
    {activeTab === "security" && <><ArcenalSecuritySettingsPanel /><AutonomySettings state={state} setState={setState} /></>}
    {activeTab === "backups" && <ArcenalBackupSettingsPanel />}
  </main>;
}

function CodexProviderCard({ state, setState, reload }: ViewProps): ReactElement {
  const [provider, setProvider] = useState<OAuthProvider | null>(null);
  const [showLogin, setShowLogin] = useState(false);
  const refresh = useCallback(async (): Promise<void> => {
    const response = await api.getOAuthProviders();
    setProvider(response.providers.find((item) => item.id === "openai-codex") ?? null);
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const authenticated = provider?.status.logged_in === true;
  const connected = authenticated && codexIsEnabled(state.config);
  const success = async (): Promise<void> => {
    await api.syncArcenalCodexProvider();
    await api.saveArcenalConfiguration({ providers: { "openai-codex": { enabled: true } } });
    setState((current) => ({ ...current, error: "", notice: "Codex est connecté et ses modèles peuvent être attribués aux agents." }));
    await Promise.all([refresh(), reload()]);
  };
  const disconnect = async (): Promise<void> => {
    if (!provider) return;
    try {
      await api.disconnectOAuthProvider(provider.id);
      await api.saveArcenalConfiguration({ providers: { "openai-codex": { enabled: false } } });
      setState((current) => ({ ...current, error: "", notice: "La connexion Codex est supprimée." }));
      await Promise.all([refresh(), reload()]);
    } catch (cause) {
      setState((current) => ({ ...current, error: errorMessage(cause), notice: "" }));
    }
  };
  const finalize = async (): Promise<void> => {
    try {
      await success();
    } catch (cause) {
      setState((current) => ({ ...current, error: errorMessage(cause), notice: "" }));
    }
  };
  const action = connected
    ? <button onClick={() => { void disconnect(); }} type="button">Déconnecter Codex</button>
    : authenticated
      ? <button className="arc-primary-button" onClick={() => { void finalize(); }} type="button"><KeyRound /> Finaliser la connexion Codex</button>
    : <button className="arc-primary-button" disabled={!provider} onClick={() => setShowLogin(true)} type="button"><KeyRound /> Connecter par device link</button>;
  return <article className="arc-provider-card" data-configured={connected}><header><span><Bot aria-hidden /></span><div><h3>OpenAI Codex</h3><small>Compte ChatGPT par lien d’appareil</small></div><em>{connected ? <><CheckCircle2 /> Configuré</> : authenticated ? "À finaliser" : "À connecter"}</em></header><p>La connexion utilise le flux officiel Codex. Ne communiquez jamais le code d’appareil à un tiers.</p><p className="arc-provider-model-note">Les modèles Codex seront attribués dans le harnais de chaque agent.</p><div className="arc-provider-actions">{action}</div>{provider && showLogin && <OAuthLoginModal provider={provider} onClose={() => setShowLogin(false)} onError={(message) => setState((current) => ({ ...current, error: message }))} onSuccess={success} />}</article>;
}

function codexIsEnabled(config: Record<string, unknown>): boolean {
  const providers = config.providers;
  if (typeof providers !== "object" || providers === null) return false;
  const codex = (providers as Record<string, unknown>)["openai-codex"];
  return typeof codex === "object" && codex !== null && (codex as Record<string, unknown>).enabled === true;
}

function SectionTitle({ icon, eyebrow, title, description }: { icon: ReactElement; eyebrow: string; title: string; description: string }): ReactElement {
  return <div className="arc-settings-section-title"><span>{icon}</span><div><small>{eyebrow}</small><h2>{title}</h2><p>{description}</p></div></div>;
}

function ProviderCard({ provider, state, setState, reload }: ProviderProps): ReactElement {
  const discovered = state.providerStatuses[provider.id]?.models ?? [];
  const catalogued = state.models.providers?.find((item) => item.slug === provider.id)?.models ?? [];
  const available = [...new Set([...catalogued, ...discovered])];
  const secret = state.secrets[provider.id] ?? "";
  const save = (): void => { void saveProvider(provider, state, setState, reload); };
  const test = (): void => { void testProvider(provider, state, setState); };
  const status = state.providerStatuses[provider.id];
  return <article className="arc-provider-card" data-configured={provider.configured}>
    <header><span><Bot aria-hidden /></span><div><h3>{provider.label}</h3><small>{provider.local ? "Moteur local ou privé" : "Service externe"}</small></div><em data-state={status?.connection}>{provider.configured ? <><CheckCircle2 /> Configuré</> : "À connecter"}</em></header>
    {provider.configurableUrl && <ProviderUrlInput provider={provider} state={state} setState={setState} />}
    {provider.keyRequired && <SecretInput provider={provider} value={secret} setState={setState} />}
    <DiscoveredModels models={available} />
    <p className="arc-provider-model-note">Les modèles sont attribués dans le harnais de chaque agent.</p>
    <label className="arc-provider-toggle"><input checked={state.enabledProviders[provider.id] !== false} onChange={(event) => setState((current) => ({ ...current, enabledProviders: { ...current.enabledProviders, [provider.id]: event.target.checked } }))} type="checkbox" /><span>Connexion active</span></label>
    {status && <p className="arc-provider-status" data-state={status.connection}>{status.message}<small>Dernier test : {formatTestDate(status.tested_at)}</small></p>}
    <div className="arc-provider-actions"><button disabled={state.busy} onClick={test} type="button">Tester la connexion</button><button className="arc-primary-button" disabled={state.busy || (provider.keyRequired && !provider.configured && !secret.trim())} onClick={save} type="button">{state.busy ? <LoaderCircle className="arc-spin" /> : <KeyRound />} {provider.configured ? "Mettre à jour" : "Connecter"}</button></div>
  </article>;
}

function DiscoveredModels({ models }: { models: string[] }): ReactElement {
  if (models.length === 0) return <p className="arc-provider-models">Aucun modèle découvert lors du dernier test.</p>;
  return <details className="arc-provider-models"><summary>{models.length} modèle{models.length === 1 ? "" : "s"} disponible{models.length === 1 ? "" : "s"}</summary><ul>{models.map((model) => <li key={model}>{model}</li>)}</ul></details>;
}

function SecretInput({ provider, value, setState }: { provider: ProviderConnection; value: string; setState: SetState }): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, secrets: { ...current.secrets, [provider.id]: event.target.value } }));
  return <label className="arc-field"><span>Clé API</span><input autoComplete="new-password" onChange={change} placeholder={provider.configured ? "Clé enregistrée — saisir pour remplacer" : "Coller la clé API"} type="password" value={value} /></label>;
}

function ProviderUrlInput({ provider, state, setState }: { provider: ProviderConnection; state: SettingsState; setState: SetState }): ReactElement {
  const change = (event: ChangeEvent<HTMLInputElement>): void => setState((current) => ({ ...current, providerUrls: { ...current.providerUrls, [provider.id]: event.target.value } }));
  return <label className="arc-field"><span>Adresse du service</span><input onChange={change} placeholder={provider.defaultBaseUrl || "https://llm.interne/v1"} type="url" value={state.providerUrls[provider.id] ?? ""} /><small>Indiquez la racine compatible OpenAI, sans identifiants dans l’URL.</small></label>;
}

async function saveProvider(provider: ProviderConnection, state: SettingsState, setState: SetState, reload: () => Promise<void>): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const secret = state.secrets[provider.id]?.trim();
    if (provider.envKey && secret) await api.setArcenalSecret(provider.envKey, secret);
    const baseUrl = state.providerUrls[provider.id]?.trim();
    const providerConfig = { providers: { [provider.id]: { base_url: baseUrl || undefined, enabled: state.enabledProviders[provider.id] !== false } } };
    await api.saveArcenalConfiguration(providerConfig);
    setState((current) => ({ ...current, notice: `${provider.label} est disponible pour ARC.`, secrets: { ...current.secrets, [provider.id]: "" } }));
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: errorMessage(cause) }));
  }
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
    await api.setArcenalSecret(key, state.customSecret.trim());
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
    await api.saveArcenalConfiguration({ approvals: { mode: level } });
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
