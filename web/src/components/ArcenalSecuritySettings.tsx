import { Activity, CheckCircle2, Clock3, LockKeyhole, Play, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type ReactElement } from "react";
import { api, type ArcenalSecurityAction, type ArcenalSecurityOverview } from "@/lib/api";
import { authorizationLabel, isArcenalSecurityOverview, riskLabel } from "@/lib/arcenal-security";

interface SecurityState {
  busy: boolean;
  error: string;
  notice: string;
  overview: ArcenalSecurityOverview | null;
  targets: Record<string, string>;
}

const INITIAL: SecurityState = { busy: true, error: "", notice: "", overview: null, targets: {} };

export function ArcenalSecuritySettingsPanel(): ReactElement {
  const { state, setState, reload } = useSecurityState();
  const execute = (action: ArcenalSecurityAction): void => { void executeAction(action, state, setState, reload); };
  return <section className="arc-settings-section"><SecurityHeader busy={state.busy} reload={reload} />
    {state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}
    {state.notice && <p className="arc-alert arc-alert-success" role="status">{state.notice}</p>}
    {state.overview && <><SecurityIdentity overview={state.overview} /><ActionCatalog actions={state.overview.actions} busy={state.busy} execute={execute} setState={setState} targets={state.targets} /><SecurityEvidence overview={state.overview} /></>}
  </section>;
}

function useSecurityState(): { state: SecurityState; setState: React.Dispatch<React.SetStateAction<SecurityState>>; reload: () => Promise<void> } {
  const [state, setState] = useState<SecurityState>(INITIAL);
  const reload = useCallback(async (): Promise<void> => {
    setState((current) => ({ ...current, busy: true, error: "" }));
    try {
      const overview = await api.getArcenalSecurityOverview();
      if (!isArcenalSecurityOverview(overview)) throw new Error("Le contrat du centre de sécurité est incomplet.");
      setState((current) => ({ ...current, busy: false, overview }));
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: message(cause) }));
    }
  }, []);
  useEffect(() => { void Promise.resolve().then(reload); }, [reload]);
  return { state, setState, reload };
}

function SecurityHeader({ busy, reload }: { busy: boolean; reload: () => Promise<void> }): ReactElement {
  return <div className="arc-settings-section-title arc-system-title"><span><LockKeyhole /></span><div><small>Sécurité</small><h2>Centre de sécurité</h2><p>Identité YunoHost, autorisations, confirmations humaines et preuves d’administration.</p></div><button className="arc-secondary-button" disabled={busy} onClick={() => void reload()} type="button"><RefreshCw /> Actualiser</button></div>;
}

function SecurityIdentity({ overview }: { overview: ArcenalSecurityOverview }): ReactElement {
  return <div className="arc-security-identity"><ShieldCheck /><dl><dt>Administrateur authentifié</dt><dd>{overview.actor.username}</dd></dl><dl><dt>Rôles YunoHost</dt><dd>{overview.actor.roles.join(" · ") || "Administrateur"}</dd></dl><Gateway label="Lecture seule" online={overview.gateways.readonly} /><Gateway label="Actions privilégiées" online={overview.gateways.control} /></div>;
}

function Gateway({ label, online }: { label: string; online: boolean }): ReactElement {
  return <dl data-online={online}><dt>{label}</dt><dd>{online ? "Disponible" : "Indisponible"}</dd></dl>;
}

function ActionCatalog({ actions, busy, execute, setState, targets }: ActionProps): ReactElement {
  return <div className="arc-security-actions"><header><div><small>Catalogue fermé</small><h3>Capacités administratives</h3></div><em>{actions.length} actions autorisées</em></header>{actions.map((action) => <ActionRow action={action} busy={busy} execute={execute} key={action.id} setState={setState} target={targets[action.id] ?? ""} />)}</div>;
}

function ActionRow({ action, busy, execute, setState, target }: ActionRowProps): ReactElement {
  const setTarget = (value: string): void => setState((current) => ({ ...current, targets: { ...current.targets, [action.id]: value } }));
  return <article data-risk={action.risk}><span><strong>{action.description}</strong><small>{authorizationLabel(action.authorization)} · Risque {riskLabel(action.risk)}</small><p>{action.consequence}</p></span>{action.allowed_targets.length > 0 && <select aria-label={`Cible de ${action.description}`} onChange={(event) => setTarget(event.target.value)} value={target}><option value="">Choisir le service</option>{action.allowed_targets.map((value) => <option key={value}>{value}</option>)}</select>}{action.authorization >= 2 && <button className="arc-secondary-button" disabled={busy || (action.allowed_targets.length > 0 && !target)} onClick={() => execute(action)} type="button"><Play /> Exécuter</button>}</article>;
}

function SecurityEvidence({ overview }: { overview: ArcenalSecurityOverview }): ReactElement {
  return <div className="arc-security-evidence"><EvidenceCard icon={<Clock3 />} title="Confirmations actives" value={String(overview.approvals.length)} text="Jetons temporaires non divulgués" /><EvidenceCard icon={overview.audit.integrity ? <CheckCircle2 /> : <ShieldAlert />} title="Intégrité du journal" value={overview.audit.integrity ? "Vérifiée" : "Compromise"} text={`${overview.audit.events.length} événements récents`} /><AuditList overview={overview} /></div>;
}

function EvidenceCard({ icon, title, value, text }: { icon: ReactElement; title: string; value: string; text: string }): ReactElement {
  return <article className="arc-security-proof">{icon}<span><small>{title}</small><strong>{value}</strong><p>{text}</p></span></article>;
}

function AuditList({ overview }: { overview: ArcenalSecurityOverview }): ReactElement {
  const events = [...overview.audit.events].reverse().slice(0, 8);
  return <article className="arc-security-audit"><header><Activity /><strong>Journal d’audit</strong></header><ul>{events.map((event) => <li key={event.hash}><span>{event.event}</span><small>{event.actor} · {formatDate(event.timestamp)}</small></li>)}{events.length === 0 && <li><span>Aucune action enregistrée</span></li>}</ul></article>;
}

async function executeAction(action: ArcenalSecurityAction, state: SecurityState, setState: SetSecurityState, reload: () => Promise<void>): Promise<void> {
  const target = state.targets[action.id]?.trim() || null;
  setState((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const initial = await api.prepareArcenalAction(action.id, target);
    const approvalId = await confirmedApproval(initial, action, target);
    await api.executeArcenalAction(action.id, target, approvalId);
    setState((current) => ({ ...current, notice: `${action.description} terminée.` }));
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: message(cause) }));
  }
}

async function confirmedApproval(initial: Awaited<ReturnType<typeof api.prepareArcenalAction>>, action: ArcenalSecurityAction, target: string | null): Promise<string | undefined> {
  if (initial.status === "ready") return undefined;
  const prompt = `${action.description}\n\nConséquence : ${action.consequence}\nRetour arrière : ${action.rollback}`;
  if (!window.confirm(prompt)) throw new Error("Action annulée par l’administrateur.");
  const confirmed = await api.prepareArcenalAction(action.id, target, true);
  if (!confirmed.approval_id) throw new Error("La confirmation renforcée n’a pas été délivrée.");
  return confirmed.approval_id;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "date inconnue" : date.toLocaleString("fr-FR");
}

function message(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Le centre de sécurité est indisponible.";
}

type SetSecurityState = React.Dispatch<React.SetStateAction<SecurityState>>;
interface ActionProps { actions: ArcenalSecurityAction[]; busy: boolean; execute: (action: ArcenalSecurityAction) => void; setState: SetSecurityState; targets: Record<string, string> }
interface ActionRowProps { action: ArcenalSecurityAction; busy: boolean; execute: (action: ArcenalSecurityAction) => void; setState: SetSecurityState; target: string }
