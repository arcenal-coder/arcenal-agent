// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ArcenalScheduledTasksPage from "./ArcenalScheduledTasksPage";

const apiMocks = vi.hoisted(() => ({
  createArcenalWorkflow: vi.fn(),
  createCronJob: vi.fn(),
  deleteCronJob: vi.fn(),
  getArcenalAutomations: vi.fn(),
  getCronJobs: vi.fn(),
  getProfiles: vi.fn(),
  pauseCronJob: vi.fn(),
  resumeCronJob: vi.fn(),
  transitionArcenalWorkflow: vi.fn(),
}));
const loadManagedAgents = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({ api: apiMocks }));
vi.mock("@/lib/arcenal-agent-manager", () => ({ loadManagedAgents }));

const ARC_AGENT = {
  application: "arcenal",
  autonomy_level: "controlled",
  description: "Architecte du serveur",
  enabled: true,
  harness: { context: "Serveur ARCenal", directives: "Superviser", memory: "" },
  id: "arc",
  knowledge_scopes: [],
  metadata: {},
  model_policy: { allowed_models: [], allowed_providers: [], denied_providers: [], local_only: false, local_preferred: true, mode: "auto" },
  name: "ARC",
  permissions: [],
  role: "architect",
  system_instructions: [],
  tools: [],
};
const DEFAULT_PROFILE = {
  description: "Agent principal",
  description_auto: false,
  distribution_name: null,
  distribution_source: null,
  distribution_version: null,
  gateway_running: true,
  has_alias: false,
  has_env: true,
  is_default: true,
  model: null,
  name: "default",
  path: "/tmp/default",
  provider: null,
  skill_count: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getCronJobs.mockResolvedValue([]);
  apiMocks.getArcenalAutomations.mockResolvedValue({ candidates: [], workflows: [] });
  apiMocks.getProfiles.mockResolvedValue({ profiles: [DEFAULT_PROFILE] });
  apiMocks.createCronJob.mockResolvedValue({ id: "daily", enabled: true });
  apiMocks.createArcenalWorkflow.mockResolvedValue({ id: "incident", status: "draft" });
  apiMocks.transitionArcenalWorkflow.mockResolvedValue({ id: "incident", status: "testing" });
  loadManagedAgents.mockResolvedValue([ARC_AGENT]);
});

afterEach(cleanup);

describe("tâches planifiées ARCenal", () => {
  it("crée une planification sans modèle global", async () => {
    render(<ArcenalScheduledTasksPage />);
    await screen.findByRole("heading", { name: "0 automatisations" });
    fireEvent.change(screen.getByLabelText("Nom"), { target: { value: "Rapport quotidien" } });
    fireEvent.change(screen.getByLabelText("Instruction"), { target: { value: "Analyse les services" } });
    fireEvent.change(screen.getByLabelText("Quand ?"), { target: { value: "every day 8am" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer en brouillon" }));
    await waitFor(() => expect(apiMocks.createCronJob).toHaveBeenCalledWith({
      deliver: "local",
      model: null,
      name: "Rapport quotidien",
      prompt: "Analyse les services",
      provider: null,
      schedule: "every day 8am",
    }, "default"));
  });

  it("crée un déclencheur rattaché au harnais de l’agent", async () => {
    render(<ArcenalScheduledTasksPage />);
    await screen.findByRole("heading", { name: "0 automatisations" });
    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "trigger" } });
    fireEvent.change(screen.getByLabelText("Nom"), { target: { value: "Incident critique" } });
    fireEvent.change(screen.getByLabelText("Instruction"), { target: { value: "Diagnostique puis notifie" } });
    fireEvent.change(screen.getByLabelText("Déclencheur"), { target: { value: "incident déclaré" } });
    fireEvent.click(screen.getByRole("button", { name: "Créer en brouillon" }));
    await waitFor(() => expect(apiMocks.createArcenalWorkflow).toHaveBeenCalledWith(expect.objectContaining({
      agent_id: "arc",
      description: "Diagnostique puis notifie",
      steps: [{ id: "response", operation: "agent_prompt", template: "Diagnostique puis notifie", tool: null }],
      trigger: "incident déclaré",
    })));
  });

  it("affiche une erreur de chargement exploitable", async () => {
    apiMocks.getCronJobs.mockRejectedValue(new Error("Registre indisponible"));
    render(<ArcenalScheduledTasksPage />);
    expect((await screen.findByRole("alert")).textContent).toContain("Registre indisponible");
  });
});
