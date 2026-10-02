import { Archive, CalendarClock, PauseCircle, PlayCircle, Plus, Trash2, Workflow } from "lucide-react";
import { useCallback, useEffect, useState, type Dispatch, type FormEvent, type ReactElement, type SetStateAction } from "react";
import { api, type ArcenalWorkflow, type CronJob, type ProfileInfo } from "@/lib/api";
import { loadManagedAgents, type ManagedAgent } from "@/lib/arcenal-agent-manager";
import { buildScheduledJob, buildTriggeredWorkflow, emptyScheduledTaskDraft, type ScheduledTaskDraft } from "@/lib/arcenal-scheduled-tasks";

interface TaskWorkspaceState {
  agents: ManagedAgent[];
  busy: boolean;
  error: string;
  jobs: CronJob[];
  profiles: ProfileInfo[];
  workflows: ArcenalWorkflow[];
}

const INITIAL_STATE: TaskWorkspaceState = { agents: [], busy: true, error: "", jobs: [], profiles: [], workflows: [] };

export default function ArcenalScheduledTasksPage(): ReactElement {
  const [state, setState] = useState(INITIAL_STATE);
  const [draft, setDraft] = useState(emptyScheduledTaskDraft());
  const reload = useCallback(async (): Promise<void> => loadWorkspace(setState), []);
  useEffect(() => { void reload(); }, [reload]);
  const create = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const created = await runAction(async () => createTask(draft), setState);
    if (!created) return;
    setDraft(emptyScheduledTaskDraft());
    await reload();
  };
  return <main className="arc-workspace arc-scheduled-tasks" aria-labelledby="scheduled-title"><WorkspaceHeading /><TaskComposer agents={state.agents} profiles={state.profiles} draft={draft} busy={state.busy} onChange={setDraft} onSubmit={create} />{state.error && <p className="arc-alert arc-alert-error" role="alert">{state.error}</p>}<TaskInventory state={state} reload={reload} setState={setState} /></main>;
}

async function loadWorkspace(setState: (state: TaskWorkspaceState) => void): Promise<void> {
  try {
    const [jobs, automations, profiles, agents] = await Promise.all([api.getCronJobs("all"), api.getArcenalAutomations(), api.getProfiles(), loadManagedAgents()]);
    setState({ agents, busy: false, error: "", jobs, profiles: profiles.profiles, workflows: automations.workflows });
  } catch (cause) {
    setState({ ...INITIAL_STATE, busy: false, error: errorMessage(cause) });
  }
}

async function createTask(draft: ScheduledTaskDraft): Promise<void> {
  if (draft.mode === "schedule") {
    await api.createCronJob(buildScheduledJob(draft), draft.agentId || "default");
    return;
  }
  await api.createArcenalWorkflow(buildTriggeredWorkflow(draft, workflowId(draft.name)));
}

function TaskComposer({ agents, profiles, draft, busy, onChange, onSubmit }: { agents: ManagedAgent[]; profiles: ProfileInfo[]; draft: ScheduledTaskDraft; busy: boolean; onChange: (draft: ScheduledTaskDraft) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }): ReactElement {
  const options = draft.mode === "schedule" ? profileOptions(profiles) : agentOptions(agents);
  const update = (field: keyof ScheduledTaskDraft, value: string): void => onChange({ ...draft, [field]: value });
  const changeMode = (mode: ScheduledTaskDraft["mode"]): void => onChange({ ...draft, agentId: firstOption(mode, agents, profiles), mode });
  return <form className="arc-task-composer" onSubmit={onSubmit}><header><span><Plus aria-hidden /></span><div><small>Langage naturel</small><h2>Créer une automatisation</h2><p>Décrivez le résultat attendu puis choisissez une planification ou un déclencheur.</p></div></header><div className="arc-form-row"><label className="arc-field"><span>Type</span><select value={draft.mode} onChange={(event) => changeMode(event.target.value as ScheduledTaskDraft["mode"])}><option value="schedule">Planification</option><option value="trigger">Déclencheur</option></select></label><label className="arc-field"><span>Agent</span><select required value={draft.agentId} onChange={(event) => update("agentId", event.target.value)}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><label className="arc-field"><span>Nom</span><input required value={draft.name} onChange={(event) => update("name", event.target.value)} /></label></div><label className="arc-field"><span>Instruction</span><textarea required rows={4} placeholder="Chaque matin, vérifie les services et prépare un compte rendu…" value={draft.instruction} onChange={(event) => update("instruction", event.target.value)} /></label>{draft.mode === "schedule" ? <label className="arc-field"><span>Quand ?</span><input required placeholder="every monday 9am, 30m ou 2026-10-05T08:00:00Z" value={draft.schedule} onChange={(event) => update("schedule", event.target.value)} /></label> : <label className="arc-field"><span>Déclencheur</span><input required placeholder="incident déclaré, document approuvé…" value={draft.trigger} onChange={(event) => update("trigger", event.target.value)} /></label>}<button className="arc-primary-button" disabled={busy || options.length === 0} type="submit">Créer en brouillon</button></form>;
}

function TaskInventory({ state, reload, setState }: { state: TaskWorkspaceState; reload: () => Promise<void>; setState: TaskStateSetter }): ReactElement {
  if (state.busy) return <section className="arc-task-inventory"><p>Chargement des automatisations…</p></section>;
  return <section className="arc-task-inventory"><header><div><small>Registre central</small><h2>{state.jobs.length + state.workflows.length} automatisation{state.jobs.length + state.workflows.length === 1 ? "" : "s"}</h2></div></header><div className="arc-task-grid">{state.jobs.map((job) => <ScheduledJobCard job={job} key={`cron-${job.id}`} reload={reload} setState={setState} />)}{state.workflows.map((workflow) => <TriggeredWorkflowCard workflow={workflow} key={`workflow-${workflow.id}`} reload={reload} setState={setState} />)}{state.jobs.length + state.workflows.length === 0 && <p>Aucune automatisation enregistrée.</p>}</div></section>;
}

function ScheduledJobCard({ job, reload, setState }: TaskCardProps): ReactElement {
  const profile = cronProfile(job);
  const toggle = (): Promise<void> => runAndReload(() => job.enabled ? api.pauseCronJob(job.id, profile) : api.resumeCronJob(job.id, profile), reload, setState);
  const remove = (): Promise<void> => runAndReload(() => api.deleteCronJob(job.id, profile), reload, setState);
  return <article className="arc-workflow-card"><header><div><strong>{job.name || job.id}</strong><span>{profile} · Planification</span></div><em>{job.enabled ? "active" : "pause"}</em></header><p>{job.prompt || "Tâche technique"}</p><small><CalendarClock aria-hidden /> {job.schedule_display || job.schedule?.display || job.schedule?.expr || job.schedule?.run_at || "Planification enregistrée"}</small><footer><button onClick={() => void toggle()} type="button">{job.enabled ? <PauseCircle /> : <PlayCircle />}{job.enabled ? "Suspendre" : "Activer"}</button><button onClick={() => void remove()} type="button"><Trash2 />Supprimer</button></footer></article>;
}

function TriggeredWorkflowCard({ workflow, reload, setState }: WorkflowCardProps): ReactElement {
  const archive = (): Promise<void> => runAndReload(() => api.transitionArcenalWorkflow(workflow.id, "archived"), reload, setState);
  const next = nextWorkflowTransition(workflow.status);
  const transition = (): Promise<void> => runAndReload(() => api.transitionArcenalWorkflow(workflow.id, next.status), reload, setState);
  return <article className="arc-workflow-card"><header><div><strong>{workflow.name}</strong><span>{workflow.agent_id} · Déclencheur</span></div><em>{workflow.status}</em></header><p>{workflow.description}</p><small><Workflow aria-hidden /> Quand « {workflow.trigger} »</small>{workflow.status !== "archived" && <footer><button onClick={() => void transition()} type="button">{next.active ? <PauseCircle /> : <PlayCircle />}{next.label}</button><button onClick={() => void archive()} type="button"><Archive />Archiver</button></footer>}</article>;
}

function nextWorkflowTransition(status: ArcenalWorkflow["status"]): { active: boolean; label: string; status: ArcenalWorkflow["status"] } {
  if (status === "draft" || status === "disabled") return { active: false, label: "Passer en test", status: "testing" };
  if (status === "testing") return { active: false, label: "Activer", status: "active" };
  return { active: true, label: "Désactiver", status: "disabled" };
}

function WorkspaceHeading(): ReactElement {
  return <header className="arc-workspace-heading"><p>Volet 2 · Automatisations</p><h1 id="scheduled-title">Tâches planifiées</h1><span>Confiez une tâche à un agent, selon une date, une fréquence ou un événement explicite.</span></header>;
}

function profileOptions(profiles: ProfileInfo[]): Array<{ label: string; value: string }> {
  const values = profiles.map((profile) => ({ label: profile.is_default ? "ARC" : profile.display_name || profile.name, value: profile.is_default ? "default" : profile.name }));
  return values.length ? values : [{ label: "ARC", value: "default" }];
}

function agentOptions(agents: ManagedAgent[]): Array<{ label: string; value: string }> {
  return agents.map((agent) => ({ label: agent.name, value: agent.id }));
}

function firstOption(mode: ScheduledTaskDraft["mode"], agents: ManagedAgent[], profiles: ProfileInfo[]): string {
  const options = mode === "schedule" ? profileOptions(profiles) : agentOptions(agents);
  return options[0]?.value ?? "";
}

function cronProfile(job: CronJob): string {
  return job.profile_name || job.profile || (job.is_default_profile ? "default" : "default");
}

function workflowId(name: string): string {
  const slug = name.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/gu, "").replace(/[^a-z0-9]+/gu, "-").replace(/^-|-$/gu, "").slice(0, 40) || "automation";
  return `${slug}-${Date.now().toString(36)}`;
}

async function runAction(action: () => Promise<unknown>, setState: TaskStateSetter): Promise<boolean> {
  try { await action(); return true; }
  catch (cause) { setState((current) => ({ ...current, busy: false, error: errorMessage(cause) })); return false; }
}

async function runAndReload(action: () => Promise<unknown>, reload: () => Promise<void>, setState: TaskStateSetter): Promise<void> {
  try { await action(); await reload(); }
  catch (cause) { setState((current) => ({ ...current, busy: false, error: errorMessage(cause) })); }
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Automatisation impossible.";
}

type TaskStateSetter = Dispatch<SetStateAction<TaskWorkspaceState>>;
interface TaskCardProps { job: CronJob; reload: () => Promise<void>; setState: TaskStateSetter }
interface WorkflowCardProps { workflow: ArcenalWorkflow; reload: () => Promise<void>; setState: TaskStateSetter }
