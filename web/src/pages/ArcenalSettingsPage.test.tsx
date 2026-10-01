// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ArcenalSettingsPage from "./ArcenalSettingsPage";

const apiMocks = vi.hoisted(() => ({
  getArcenalConfiguration: vi.fn(),
  getArcenalProviderStatuses: vi.fn(),
  getModelOptions: vi.fn(),
  saveArcenalConfiguration: vi.fn(),
  setArcenalSecret: vi.fn(),
  setModelAssignment: vi.fn(),
  testArcenalProvider: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMocks }));
vi.mock("@/components/ArcenalGeneralSettings", () => ({ ArcenalGeneralSettingsPanel: () => null }));
vi.mock("@/components/ArcenalAppearanceSettings", () => ({ ArcenalAppearanceSettingsPanel: () => null }));
vi.mock("@/components/ArcenalManagedFilesSettings", () => ({ ArcenalManagedFilesSettingsPanel: () => null }));
vi.mock("@/components/ArcenalMemorySettings", () => ({ ArcenalMemorySettingsPanel: () => null }));
vi.mock("@/components/ArcenalFrugalSettings", () => ({ ArcenalFrugalSettingsPanel: () => null }));
vi.mock("@/components/ArcenalAutomationsSettings", () => ({ ArcenalAutomationsSettingsPanel: () => null }));
vi.mock("@/components/ArcenalAccessManager", () => ({ ArcenalAccessManager: () => null }));
vi.mock("@/components/ArcenalCapabilitiesSettings", () => ({ ArcenalCapabilitiesSettings: () => null }));
vi.mock("@/components/ArcenalSystemSettings", () => ({ ArcenalBackupSettingsPanel: () => null, ArcenalSystemSettingsPanel: () => null }));
vi.mock("@/components/ArcenalSecuritySettings", () => ({ ArcenalSecuritySettingsPanel: () => null }));

const CONFIGURATION = {
  backend: "arc",
  config: { model: { default: "auto", provider: "gemini" }, providers: {} },
  migration: { conflicts: [], copied: 2, state: "complete", unchanged: 0 },
  secrets: { GEMINI_API_KEY: true },
  vault: "ready",
};

const MODELS = {
  model: "auto",
  provider: "gemini",
  providers: [{ models: ["gemini-3.6-flash"], name: "Google Gemini", slug: "gemini" }],
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getArcenalConfiguration.mockResolvedValue(CONFIGURATION);
  apiMocks.getArcenalProviderStatuses.mockResolvedValue({ providers: {} });
  apiMocks.getModelOptions.mockResolvedValue(MODELS);
  apiMocks.saveArcenalConfiguration.mockResolvedValue({ ok: true });
  apiMocks.setModelAssignment.mockResolvedValue({ ok: true });
});

afterEach(cleanup);

async function geminiCard(): Promise<HTMLElement> {
  fireEvent.click(screen.getByRole("button", { name: "Fournisseurs IA" }));
  await screen.findByText("Configuré");
  return screen.getByRole("heading", { name: "Google Gemini" }).closest("article") as HTMLElement;
}

describe("paramètres des fournisseurs ARC", () => {
  it("synchronise le modèle natif ARC avec le moteur conversationnel", async () => {
    render(<ArcenalSettingsPage />);
    const card = await geminiCard();
    const mainModel = within(card).getByLabelText("Modèle principal");
    fireEvent.change(mainModel, { target: { value: "gemini-3.6-flash" } });
    fireEvent.click(within(card).getByRole("button", { name: "Mettre à jour" }));
    await waitFor(() => expect(apiMocks.setModelAssignment).toHaveBeenCalledWith({
      base_url: "https://generativelanguage.googleapis.com/v1beta",
      model: "gemini-3.6-flash",
      provider: "gemini",
      scope: "main",
    }));
  });

  it("refuse le pseudo-modèle auto pour un fournisseur direct", async () => {
    render(<ArcenalSettingsPage />);
    const card = await geminiCard();
    fireEvent.click(within(card).getByRole("button", { name: "Mettre à jour" }));
    expect((await screen.findByRole("alert")).textContent).toContain("modèle précis");
    expect(apiMocks.saveArcenalConfiguration).not.toHaveBeenCalled();
    expect(apiMocks.setModelAssignment).not.toHaveBeenCalled();
  });

  it("propage l’échec du moteur sans annoncer une connexion disponible", async () => {
    apiMocks.setModelAssignment.mockRejectedValue(new Error("Modèle indisponible"));
    render(<ArcenalSettingsPage />);
    const card = await geminiCard();
    fireEvent.change(within(card).getByLabelText("Modèle principal"), { target: { value: "gemini-3.6-flash" } });
    fireEvent.click(within(card).getByRole("button", { name: "Mettre à jour" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Modèle indisponible");
    expect(screen.queryByText("Google Gemini est disponible pour ARC.")).toBeNull();
  });
});
