import type { ArcenalWorkflowCreate, CronJobMutation } from "./api";

export type TaskCreationMode = "schedule" | "trigger";

export interface ScheduledTaskDraft {
  agentId: string;
  instruction: string;
  mode: TaskCreationMode;
  name: string;
  schedule: string;
  trigger: string;
}

export class ScheduledTaskDraftError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ScheduledTaskDraftError";
  }
}

export function emptyScheduledTaskDraft(): ScheduledTaskDraft {
  return { agentId: "default", instruction: "", mode: "schedule", name: "", schedule: "", trigger: "" };
}

export function buildScheduledJob(draft: ScheduledTaskDraft): CronJobMutation {
  const common = validatedCommon(draft);
  const schedule = required(draft.schedule, "La planification est obligatoire.");
  return { deliver: "local", model: null, name: common.name, prompt: common.instruction, provider: null, schedule };
}

export function buildTriggeredWorkflow(draft: ScheduledTaskDraft, id: string): ArcenalWorkflowCreate {
  const common = validatedCommon(draft);
  const trigger = required(draft.trigger, "Le déclencheur est obligatoire.");
  const agentId = required(draft.agentId, "Choisissez l’agent chargé de cette tâche.");
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/u.test(id)) throw new ScheduledTaskDraftError("Identifiant d’automatisation invalide.");
  return { agent_id: agentId, autonomy: "controlled", description: common.instruction, exceptions: 0, executions: 0, id, name: common.name, permissions: [], steps: [{ id: "response", operation: "agent_prompt", template: common.instruction, tool: null }], trigger, version: 1 };
}

function validatedCommon(draft: ScheduledTaskDraft): { instruction: string; name: string } {
  return {
    instruction: required(draft.instruction, "Décrivez la tâche en langage naturel."),
    name: required(draft.name, "Le nom de la tâche est obligatoire."),
  };
}

function required(value: string, message: string): string {
  const normalized = value.trim();
  if (!normalized) throw new ScheduledTaskDraftError(message);
  return normalized;
}
