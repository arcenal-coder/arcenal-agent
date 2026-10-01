// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ArcenalFrugalSettingsPanel } from "./ArcenalFrugalSettings";

const apiMocks = vi.hoisted(() => ({ getArcenalFrugalOverview: vi.fn(), saveArcenalModel: vi.fn(), saveArcenalProvider: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: apiMocks }));

const OVERVIEW = {
  metrics: { total_requests: 5, llm_requests: 2, non_llm_requests: 3, cache_hits: 1, deterministic_hits: 1, workflow_hits: 1, input_tokens: 20, output_tokens: 10, tokens_avoided_estimate: 15, actual_estimated_cost: 0.2, estimated_cost_avoided: 0.1, average_routing_latency_ms: 1.4, average_total_latency_ms: 80, average_rag_latency_ms: 4, average_context_tokens: 120, provider_failures: 0, by_provider: { openrouter: 2 }, by_model: { small: 2 } },
  providers: [{ id: "openrouter", name: "OpenRouter", type: "openrouter", enabled: true, base_url: "https://openrouter.ai/api/v1", authentication_type: "bearer", secret_reference: "OPENROUTER_API_KEY", location: "remote", jurisdiction: null, capabilities: ["chat", "token_usage"], priority: 100, health: "healthy" }],
  models: [{ id: "small", provider: "openrouter", model_name: "small", enabled: true, capabilities: ["light"], context_window: 32000, supports_tools: false, supports_structured_output: true, supports_vision: false, privacy_class: "internal", location: "remote", hosting_region: null, input_cost: 0.1, output_cost: 0.2, priority: 10 }],
  traces: [{ request_id: "request-1", execution_mode: "llm", provider: "openrouter", model: "small", input_tokens: 10, output_tokens: 5, estimated_cost: 0.02, duration_ms: 80, rag_duration_ms: 4, context_tokens: 120, provider_attempts: 1, provider_failures: 0 }],
} as const;

beforeEach(() => { vi.clearAllMocks(); apiMocks.getArcenalFrugalOverview.mockResolvedValue(OVERVIEW); apiMocks.saveArcenalModel.mockResolvedValue({ ...OVERVIEW.models[0], enabled: false }); apiMocks.saveArcenalProvider.mockResolvedValue({ ...OVERVIEW.providers[0], enabled: false }); });
afterEach(cleanup);

describe("ARC Frugal", () => {
  it("affiche uniquement les économies mesurées et la route récente", async () => {
    render(<ArcenalFrugalSettingsPanel />);
    expect(await screen.findByText("Échecs fournisseur")).toBeTruthy();
    expect(screen.getByText("openrouter · small")).toBeTruthy();
  });

  it("administre un fournisseur sans afficher son secret", async () => {
    render(<ArcenalFrugalSettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Désactiver le fournisseur OpenRouter" }));
    await waitFor(() => expect(apiMocks.saveArcenalProvider).toHaveBeenCalledWith(expect.objectContaining({ id: "openrouter", enabled: false, secret_reference: "OPENROUTER_API_KEY" })));
    expect(screen.queryByText(/sk-/)).toBeNull();
  });

  it("désactive un modèle via le backend", async () => {
    render(<ArcenalFrugalSettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Désactiver le modèle small" }));
    await waitFor(() => expect(apiMocks.saveArcenalModel).toHaveBeenCalledWith(expect.objectContaining({ id: "small", enabled: false })));
  });
});
