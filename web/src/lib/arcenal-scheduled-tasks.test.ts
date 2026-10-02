import { describe, expect, it } from "vitest";
import { buildScheduledJob, buildTriggeredWorkflow, emptyScheduledTaskDraft } from "./arcenal-scheduled-tasks";

describe("tâches planifiées ARCenal", () => {
  it("crée une tâche planifiée sans modèle hérité du fournisseur", () => {
    const draft = { ...emptyScheduledTaskDraft(), agentId: "veille", instruction: "Contrôle les alertes réglementaires", name: "Veille quotidienne", schedule: "every day 8am" };

    expect(buildScheduledJob(draft)).toMatchObject({ model: null, prompt: draft.instruction, provider: null, schedule: draft.schedule });
  });

  it("crée un déclencheur gouverné pour un agent", () => {
    const draft = { ...emptyScheduledTaskDraft(), agentId: "arc", instruction: "Prépare un diagnostic", mode: "trigger" as const, name: "Incident", trigger: "incident déclaré" };

    expect(buildTriggeredWorkflow(draft, "incident-1")).toMatchObject({ agent_id: "arc", autonomy: "controlled", steps: [{ operation: "agent_prompt" }], trigger: "incident déclaré" });
  });

  it("refuse une tâche incomplète ou un identifiant invalide", () => {
    expect(() => buildScheduledJob(emptyScheduledTaskDraft())).toThrow("langage naturel");
    expect(() => buildTriggeredWorkflow({ ...emptyScheduledTaskDraft(), instruction: "Agir", name: "Test", trigger: "signal" }, "INVALIDE" )).toThrow("invalide");
  });
});
