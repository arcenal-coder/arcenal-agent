import { useCallback, useEffect, useMemo, useState, type ReactElement } from "react";
import { Activity, LockKeyhole, Search, ShieldAlert, SlidersHorizontal, Wrench } from "lucide-react";
import { api, type ArcenalCapabilityRisk } from "@/lib/api";
import { capabilityViews, isCapabilitiesResponse, type CapabilityView } from "@/lib/arcenal-capabilities";

type OriginFilter = "all" | "arcenal" | "hermes";
type RiskFilter = "all" | ArcenalCapabilityRisk;

interface CapabilityState {
  busyId: string;
  error: string;
  items: CapabilityView[];
  loading: boolean;
}

const INITIAL_STATE: CapabilityState = { busyId: "", error: "", items: [], loading: true };

export function ArcenalCapabilitiesSettings(): ReactElement {
  const [state, setState] = useState<CapabilityState>(INITIAL_STATE);
  const [origin, setOrigin] = useState<OriginFilter>("all");
  const [risk, setRisk] = useState<RiskFilter>("all");
  const [query, setQuery] = useState("");
  const load = useCallback(async (): Promise<void> => {
    try {
      const [response, toolsets] = await Promise.all([api.getArcenalCapabilities(), api.getToolsets()]);
      if (!isCapabilitiesResponse(response)) throw new Error("L’inventaire des capacités est incomplet.");
      setState({ busyId: "", error: "", items: capabilityViews(response, toolsets), loading: false });
    } catch (cause) {
      setState((current) => ({ ...current, error: errorMessage(cause), loading: false }));
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const visible = useMemo(() => filterCapabilities(state.items, query, origin, risk), [state.items, query, origin, risk]);
  const toggle = (item: CapabilityView): void => { void toggleCapability(item, setState, load); };
  return <section className="arc-settings-section"><CapabilityTitle />
    <CapabilityFilters origin={origin} query={query} risk={risk} setOrigin={setOrigin} setQuery={setQuery} setRisk={setRisk} />
    {state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}
    {state.loading ? <p className="arc-settings-status">Inventaire des capacités en cours…</p> : <CapabilityList busyId={state.busyId} items={visible} toggle={toggle} />}
  </section>;
}

function CapabilityTitle(): ReactElement {
  return <div className="arc-settings-section-title"><span><Wrench /></span><div><small>Outils et capacités</small><h2>Autorisations du moteur</h2><p>ARC distingue ses outils gouvernés des capacités techniques héritées de Hermes et journalise leur utilisation sans conserver les arguments.</p></div></div>;
}

function CapabilityFilters({ origin, query, risk, setOrigin, setQuery, setRisk }: { origin: OriginFilter; query: string; risk: RiskFilter; setOrigin: (value: OriginFilter) => void; setQuery: (value: string) => void; setRisk: (value: RiskFilter) => void }): ReactElement {
  return <div className="arc-capability-filters"><label><Search /><input aria-label="Rechercher une capacité" onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher un outil…" value={query} /></label><label><span>Origine</span><select onChange={(event) => setOrigin(event.target.value as OriginFilter)} value={origin}><option value="all">Toutes</option><option value="arcenal">ARCenal</option><option value="hermes">Hermes</option></select></label><label><span>Risque</span><select onChange={(event) => setRisk(event.target.value as RiskFilter)} value={risk}><option value="all">Tous</option><option value="none">Aucun</option><option value="low">Faible</option><option value="medium">Moyen</option><option value="high">Élevé</option></select></label></div>;
}

function CapabilityList({ busyId, items, toggle }: { busyId: string; items: CapabilityView[]; toggle: (item: CapabilityView) => void }): ReactElement {
  if (!items.length) return <p className="arc-settings-status">Aucune capacité ne correspond à ces filtres.</p>;
  return <div className="arc-capability-list">{items.map((item) => <CapabilityCard busy={busyId === item.id} item={item} key={`${item.origin}-${item.id}`} toggle={toggle} />)}</div>;
}

function CapabilityCard({ busy, item, toggle }: { busy: boolean; item: CapabilityView; toggle: (item: CapabilityView) => void }): ReactElement {
  return <article className="arc-capability-card" data-enabled={item.enabled} data-risk={item.risk}><header><span>{item.origin === "arcenal" ? <ShieldAlert /> : <SlidersHorizontal />}</span><div><strong>{item.name}</strong><small>{item.origin === "arcenal" ? "ARCenal · gouverné" : "Hermes · hérité"}</small></div><em>{item.enabled ? "Actif" : "Désactivé"}</em></header><p>{item.description}</p><dl><div><dt>Permission</dt><dd>{item.permission}</dd></div><div><dt>Risque</dt><dd>{riskLabel(item.risk)}</dd></div><div><dt>Confirmation</dt><dd>{item.confirmation ? "Obligatoire" : "Non requise"}</dd></div><div><dt>Dernière utilisation</dt><dd>{usageLabel(item)}</dd></div></dl><div className="arc-capability-tools">{item.tools.slice(0, 6).map((tool) => <code key={tool}>{tool}</code>)}{item.tools.length > 6 && <small>+{item.tools.length - 6}</small>}</div><button disabled={busy || !item.mutable} onClick={() => toggle(item)} type="button">{item.mutable ? <><Activity /> {item.enabled ? "Désactiver" : "Activer"}</> : <><LockKeyhole /> Protégé par ARCenal</>}</button></article>;
}

function filterCapabilities(items: CapabilityView[], query: string, origin: OriginFilter, risk: RiskFilter): CapabilityView[] {
  const needle = query.trim().toLocaleLowerCase("fr");
  return items.filter((item) => {
    if (origin !== "all" && item.origin !== origin) return false;
    if (risk !== "all" && item.risk !== risk) return false;
    return !needle || `${item.name} ${item.description} ${item.tools.join(" ")}`.toLocaleLowerCase("fr").includes(needle);
  });
}

async function toggleCapability(item: CapabilityView, setState: React.Dispatch<React.SetStateAction<CapabilityState>>, reload: () => Promise<void>): Promise<void> {
  if (!item.mutable) return;
  if (!item.enabled && item.risk === "high" && !window.confirm(`Activer la capacité sensible « ${item.name} » ?`)) return;
  setState((current) => ({ ...current, busyId: item.id, error: "" }));
  try {
    await api.toggleToolset(item.id, !item.enabled);
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busyId: "", error: errorMessage(cause) }));
  }
}

function usageLabel(item: CapabilityView): string {
  if (!item.lastUsage) return "Jamais observée";
  const date = new Date(item.lastUsage.last_used);
  const rendered = Number.isNaN(date.getTime()) ? "date inconnue" : date.toLocaleString("fr-FR");
  return `${rendered} · ${item.lastUsage.last_status} · ${item.lastUsage.count} appel(s)`;
}

function riskLabel(risk: ArcenalCapabilityRisk): string {
  return { high: "Élevé", low: "Faible", medium: "Moyen", none: "Aucun" }[risk];
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Les capacités n’ont pas pu être chargées.";
}
