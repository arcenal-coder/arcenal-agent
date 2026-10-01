import { Archive, CheckCircle2, FlaskConical, PauseCircle, Workflow } from "lucide-react";
import { useEffect, useState, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { api, type ArcenalAutomationsResponse, type ArcenalWorkflow, type ArcenalWorkflowStatus } from "@/lib/api";

interface AutomationState { busy: boolean; data: ArcenalAutomationsResponse | null; error: string; }

export function ArcenalAutomationsSettingsPanel(): ReactElement {
  const [state, setState] = useState<AutomationState>({ busy: true, data: null, error: "" });
  const reload = (): Promise<void> => loadAutomations(setState);
  useEffect(() => { void loadAutomations(setState); }, []);
  if (state.busy) return <section className="arc-settings-section"><p>Chargement des workflows…</p></section>;
  if (!state.data) return <section className="arc-settings-section"><p className="arc-alert arc-alert-error">{state.error}</p></section>;
  return <AutomationView data={state.data} reload={reload} />;
}

async function loadAutomations(setState: Dispatch<SetStateAction<AutomationState>>): Promise<void> {
  try { setState({ busy: false, data: await api.getArcenalAutomations(), error: "" }); }
  catch (cause) { setState({ busy: false, data: null, error: errorMessage(cause) }); }
}

function AutomationView({ data, reload }: { data: ArcenalAutomationsResponse; reload: () => Promise<void> }): ReactElement {
  return <section className="arc-settings-section arc-frugal"><header className="arc-frugal-title"><Workflow /><div><small>Gouvernance</small><h2>Automatisations</h2><p>Les processus détectés restent candidats jusqu'à leur revue, leur test et leur approbation humaine.</p></div></header><div className="arc-frugal-panel"><h3>Workflows gouvernés</h3>{data.workflows.length === 0 ? <p>Aucun workflow enregistré.</p> : data.workflows.map((workflow) => <WorkflowCard key={workflow.id} workflow={workflow} reload={reload} />)}</div><div className="arc-frugal-panel"><h3>Candidats détectés</h3>{data.candidates.length === 0 ? <p>Aucun processus assez stable n'a encore été proposé.</p> : data.candidates.map((candidate) => <article className="arc-model-row" key={candidate.id}><div><strong>{candidate.name}</strong><span>{candidate.observations} observations · confiance {(candidate.confidence * 100).toFixed(0)} %</span><small>Risque {candidate.risk_level} · économie mesurée {candidate.estimated_savings.toFixed(4)}</small></div></article>)}</div></section>;
}

function WorkflowCard({ workflow, reload }: { workflow: ArcenalWorkflow; reload: () => Promise<void> }): ReactElement {
  const actions = workflowActions(workflow.status);
  const transition = async (status: ArcenalWorkflowStatus): Promise<void> => { await api.transitionArcenalWorkflow(workflow.id, status); await reload(); };
  return <article className="arc-workflow-card"><header><div><strong>{workflow.name}</strong><span>{workflow.agent_id} · v{workflow.version} · {workflow.autonomy}</span></div><em>{workflow.status}</em></header><p>{workflow.description}</p><small>Déclencheur : {workflow.trigger} · {workflow.executions} exécutions · {workflow.exceptions} exceptions</small><footer>{actions.map((action) => <button key={action.status} onClick={() => void transition(action.status)} type="button">{action.icon}{action.label}</button>)}</footer></article>;
}

function workflowActions(status: ArcenalWorkflowStatus): Array<{ status: ArcenalWorkflowStatus; label: string; icon: ReactElement }> {
  if (status === "draft") return [{ status: "testing", label: "Tester", icon: <FlaskConical /> }, { status: "archived", label: "Archiver", icon: <Archive /> }];
  if (status === "testing") return [{ status: "active", label: "Approuver et activer", icon: <CheckCircle2 /> }, { status: "disabled", label: "Désactiver", icon: <PauseCircle /> }];
  if (status === "active") return [{ status: "disabled", label: "Désactiver", icon: <PauseCircle /> }, { status: "archived", label: "Archiver", icon: <Archive /> }];
  if (status === "disabled") return [{ status: "testing", label: "Retester", icon: <FlaskConical /> }, { status: "archived", label: "Archiver", icon: <Archive /> }];
  return [];
}

function errorMessage(cause: unknown): string { return cause instanceof Error ? cause.message : "Automatisations indisponibles."; }
