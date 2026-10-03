import { describe, expect, it } from "vitest";
import { buildScheduledWorkflow, buildTriggeredWorkflow, emptyScheduledTaskDraft } from "./arcenal-scheduled-tasks";

describe("tâches planifiées ARCenal", () => {
  it("crée une tâche planifiée gouvernée sans modèle fournisseur", () => {
    const draft = { ...emptyScheduledTaskDraft(), agentId: "veille", instruction: "Contrôle les alertes réglementaires", name: "Veille quotidienne", schedule: "every day 8am" };

    expect(buildScheduledWorkflow(draft, "veille-1")).toMatchObject({ agent_id: "veille", profile_name: "veille", schedule: draft.schedule, steps: [{ operation: "agent_prompt" }] });
  });

  it("crée un déclencheur gouverné pour un agent", () => {
    const draft = { ...emptyScheduledTaskDraft(), agentId: "arc", instruction: "Prépare un diagnostic", mode: "trigger" as const, name: "Incident", trigger: "incident déclaré" };

    expect(buildTriggeredWorkflow(draft, "incident-1")).toMatchObject({ agent_id: "arc", autonomy: "controlled", steps: [{ operation: "agent_prompt" }], trigger: "incident déclaré" });
  });

  it("refuse une tâche incomplète ou un identifiant invalide", () => {
    expect(() => buildScheduledWorkflow(emptyScheduledTaskDraft(), "test-1")).toThrow("langage naturel");
    expect(() => buildTriggeredWorkflow({ ...emptyScheduledTaskDraft(), instruction: "Agir", name: "Test", trigger: "signal" }, "INVALIDE" )).toThrow("invalide");
  });
});
