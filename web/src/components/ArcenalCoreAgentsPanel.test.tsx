// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ArcenalFrugalOverview, ArcenalModelDescriptor } from "@/lib/api";
import { ArcenalCoreAgentsPanel } from "./ArcenalCoreAgentsPanel";

const apiMocks = vi.hoisted(() => ({ fetchJSON: vi.fn(), getOverview: vi.fn(), saveModel: vi.fn() }));

vi.mock("@/lib/api", () => ({
  api: { getArcenalFrugalOverview: apiMocks.getOverview, saveArcenalModel: apiMocks.saveModel },
  fetchJSON: apiMocks.fetchJSON,
}));

const model = (id: string, provider: string, privacy: ArcenalModelDescriptor["privacy_class"]): ArcenalModelDescriptor => ({
  availability: "available", capabilities: ["standard"], catalog_source: "discovered", context_window: null,
  display_name: id, enabled: true, hosting_region: null, id, input_cost: 0, location: "remote",
  model_name: id, output_cost: 0, priority: 10, privacy_class: privacy, provider,
  supports_structured_output: true, supports_tools: true, supports_vision: false,
});

const OVERVIEW: ArcenalFrugalOverview = {
  metrics: { total_requests: 0, llm_requests: 0, non_llm_requests: 0, cache_hits: 0, deterministic_hits: 0, workflow_hits: 0, input_tokens: 0, output_tokens: 0, tokens_avoided_estimate: 0, actual_estimated_cost: 0, estimated_cost_avoided: 0, average_routing_latency_ms: 0, average_total_latency_ms: 0, average_rag_latency_ms: 0, average_context_tokens: 0, provider_failures: 0, by_provider: {}, by_model: {} },
  models: [model("gemini-admin", "gemini", "admin"), model("openrouter-internal", "openrouter", "internal")],
  providers: [], traces: [],
};

const AGENT = {
  application: "arcenal-system", autonomy_level: "approval_required", description: "Architecte", enabled: true,
  harness: { context: "", directives: "", memory: "" }, id: "arc", knowledge_scopes: ["system"], metadata: {},
  model_policy: { allowed_models: [], allowed_providers: [], denied_providers: [], local_only: false, local_preferred: true, mode: "auto" },
  name: "ARC", permissions: ["system.admin"], role: "architect", system_instructions: [], tools: [],
};

describe("sélection du fournisseur d’un agent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.fetchJSON
      .mockResolvedValueOnce({ agents: [AGENT] })
      .mockResolvedValueOnce(AGENT)
      .mockResolvedValue({ agents: [AGENT] });
    apiMocks.getOverview.mockResolvedValue(OVERVIEW);
    apiMocks.saveModel.mockImplementation((value: ArcenalModelDescriptor) => Promise.resolve(value));
  });
  afterEach(cleanup);

  it("affiche OpenRouter et exige une autorisation explicite pour ARC", async () => {
    render(<ArcenalCoreAgentsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Ouvrir la fiche" }));
    fireEvent.change(screen.getByLabelText("Mode"), { target: { value: "fixed" } });
    const provider = screen.getByLabelText("Fournisseur");

    expect(within(provider).getByRole("option", { name: "openrouter" })).toBeTruthy();
    fireEvent.change(provider, { target: { value: "openrouter" } });
    fireEvent.change(screen.getByLabelText("Modèle"), { target: { value: "openrouter-internal" } });
    fireEvent.click(screen.getByRole("button", { name: /Autoriser ce modèle/ }));

    await waitFor(() => expect(apiMocks.saveModel).toHaveBeenCalledWith(expect.objectContaining({ id: "openrouter-internal", privacy_class: "admin" })));
    await waitFor(() => expect(apiMocks.fetchJSON).toHaveBeenCalledWith(expect.stringContaining("/arc"), expect.objectContaining({ method: "PATCH" })));
  });

  it("n’attribue pas le modèle si son autorisation échoue", async () => {
    apiMocks.saveModel.mockRejectedValue(new Error("Autorisation refusée"));
    render(<ArcenalCoreAgentsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Ouvrir la fiche" }));
    fireEvent.change(screen.getByLabelText("Mode"), { target: { value: "fixed" } });
    fireEvent.change(screen.getByLabelText("Fournisseur"), { target: { value: "openrouter" } });
    fireEvent.change(screen.getByLabelText("Modèle"), { target: { value: "openrouter-internal" } });
    fireEvent.click(screen.getByRole("button", { name: /Autoriser ce modèle/ }));

    expect(await screen.findByText("Autorisation refusée")).toBeTruthy();
    expect(apiMocks.fetchJSON).not.toHaveBeenCalledWith(expect.stringContaining("/arc"), expect.objectContaining({ method: "PATCH" }));
  });
});
