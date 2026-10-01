import { Activity, BrainCircuit, Coins, Gauge, Network, Route } from "lucide-react";
import { useEffect, useState, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { api, type ArcenalFrugalOverview, type ArcenalModelDescriptor, type ArcenalProviderDescriptor } from "@/lib/api";

interface FrugalState { busy: boolean; error: string; overview: ArcenalFrugalOverview | null; }
const INITIAL_STATE: FrugalState = { busy: true, error: "", overview: null };

export function ArcenalFrugalSettingsPanel(): ReactElement {
  const [state, setState] = useState<FrugalState>(INITIAL_STATE);
  const reload = (): Promise<void> => loadFrugal(setState);
  useEffect(() => { void loadFrugal(setState); }, []);
  if (state.busy) return <section className="arc-settings-section"><p>Chargement des mesures réelles…</p></section>;
  if (state.error || !state.overview) return <section className="arc-settings-section"><p className="arc-alert arc-alert-error">{state.error}</p></section>;
  return <FrugalOverviewView overview={state.overview} reload={reload} />;
}

async function loadFrugal(setState: Dispatch<SetStateAction<FrugalState>>): Promise<void> {
  try { setState({ busy: false, error: "", overview: await api.getArcenalFrugalOverview() }); }
  catch (cause) { setState({ busy: false, error: errorMessage(cause), overview: null }); }
}

function FrugalOverviewView({ overview, reload }: { overview: ArcenalFrugalOverview; reload: () => Promise<void> }): ReactElement {
  const metrics = overview.metrics;
  const cards = [["Requêtes", metrics.total_requests], ["Appels LLM", metrics.llm_requests], ["Sans LLM", metrics.non_llm_requests], ["Cache", metrics.cache_hits], ["Déterministe", metrics.deterministic_hits], ["Workflows", metrics.workflow_hits], ["Échecs fournisseur", metrics.provider_failures], ["Latence totale", `${metrics.average_total_latency_ms.toFixed(1)} ms`]] as const;
  return <section className="arc-settings-section arc-frugal"><header className="arc-frugal-title"><BrainCircuit /><div><small>ARC Frugal</small><h2>IA & consommation</h2><p>La ressource minimale suffisante, avec une économie fondée sur les exécutions observées.</p></div></header><div className="arc-frugal-metrics">{cards.map(([label, value]) => <article key={label}><strong>{value}</strong><span>{label}</span></article>)}</div><ProviderRegistry providers={overview.providers} reload={reload} /><ModelRegistry models={overview.models} reload={reload} /><TraceList traces={overview.traces} /></section>;
}

function ProviderRegistry({ providers, reload }: { providers: ArcenalProviderDescriptor[]; reload: () => Promise<void> }): ReactElement {
  const save = async (provider: ArcenalProviderDescriptor, values: Partial<ArcenalProviderDescriptor>): Promise<void> => { await api.saveArcenalProvider({ ...provider, ...values }); await reload(); };
  return <div className="arc-frugal-panel"><h3><Network /> Fournisseurs interchangeables</h3>{providers.map((provider) => <article className="arc-model-row" key={provider.id}><div><strong>{provider.name}</strong><span>{provider.location} · santé {provider.health}</span><small>{provider.capabilities.join(" · ")}</small></div><div><label>Priorité <input aria-label={`Priorité ${provider.name}`} defaultValue={provider.priority} min="0" onBlur={(event) => void save(provider, { priority: Number(event.target.value) })} type="number" /></label><button aria-label={`${provider.enabled ? "Désactiver" : "Activer"} le fournisseur ${provider.name}`} onClick={() => void save(provider, { enabled: !provider.enabled })} type="button">{provider.enabled ? "Désactiver" : "Activer"}</button></div></article>)}</div>;
}

function ModelRegistry({ models, reload }: { models: ArcenalModelDescriptor[]; reload: () => Promise<void> }): ReactElement {
  const toggle = async (model: ArcenalModelDescriptor): Promise<void> => { await api.saveArcenalModel({ ...model, enabled: !model.enabled }); await reload(); };
  return <div className="arc-frugal-panel"><h3><Route /> Routage et modèles</h3>{models.length === 0 ? <p>Aucun modèle déclaré dans le registre.</p> : models.map((model) => <article className="arc-model-row" key={model.id}><div><strong>{model.model_name}</strong><span>{model.provider} · {model.location} · priorité {model.priority}</span><small>{model.capabilities.join(" · ")} · confidentialité {model.privacy_class}</small></div><div><span><Coins /> {(model.input_cost + model.output_cost).toFixed(4)}</span><button aria-label={`${model.enabled ? "Désactiver" : "Activer"} le modèle ${model.model_name}`} onClick={() => void toggle(model)} type="button">{model.enabled ? "Désactiver" : "Activer"}</button></div></article>)}</div>;
}

function TraceList({ traces }: { traces: ArcenalFrugalOverview["traces"] }): ReactElement {
  return <div className="arc-frugal-panel"><h3><Activity /> Décisions récentes</h3>{traces.length === 0 ? <p>Aucune exécution mesurée.</p> : traces.slice().reverse().map((trace) => <article className="arc-trace-row" key={trace.request_id}><Gauge /><div><strong>{trace.execution_mode}</strong><span>{trace.provider || "sans fournisseur"} · {trace.model || "sans modèle"}</span></div><small>{trace.duration_ms.toFixed(0)} ms · RAG {trace.rag_duration_ms.toFixed(0)} ms · {trace.input_tokens + trace.output_tokens} tokens</small></article>)}</div>;
}

function errorMessage(cause: unknown): string { return cause instanceof Error ? cause.message : "ARC Frugal est indisponible."; }
