// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ArcenalSettingsPage from "./ArcenalSettingsPage";

const apiMocks = vi.hoisted(() => ({
  getArcenalConfiguration: vi.fn(),
  getArcenalProviderStatuses: vi.fn(),
  getOAuthProviders: vi.fn(),
  getModelOptions: vi.fn(),
  saveArcenalConfiguration: vi.fn(),
  setArcenalSecret: vi.fn(),
  syncArcenalCodexProvider: vi.fn(),
  disconnectOAuthProvider: vi.fn(),
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
  apiMocks.getOAuthProviders.mockResolvedValue({ providers: [{ id: "openai-codex", name: "OpenAI Codex", flow: "device_code", cli_command: "codex login --device-auth", docs_url: "https://developers.openai.com/", status: { logged_in: false } }] });
  apiMocks.getModelOptions.mockResolvedValue(MODELS);
  apiMocks.saveArcenalConfiguration.mockResolvedValue({ ok: true });
  apiMocks.syncArcenalCodexProvider.mockResolvedValue({ configured: true, models: ["gpt-test"], provider: "openai-codex" });
});

afterEach(cleanup);

async function geminiCard(): Promise<HTMLElement> {
  fireEvent.click(screen.getByRole("button", { name: "Fournisseurs IA" }));
  await screen.findByText("Configuré");
  return screen.getByRole("heading", { name: "Google Gemini" }).closest("article") as HTMLElement;
}

describe("paramètres des fournisseurs ARC", () => {
  it("propose la connexion Codex par lien d’appareil", async () => {
    render(<ArcenalSettingsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Fournisseurs IA" }));

    expect(await screen.findByRole("heading", { name: "OpenAI Codex" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Connecter par device link/ })).toBeTruthy();
  });

  it("permet de supprimer une connexion Codex déjà active", async () => {
    apiMocks.getOAuthProviders.mockResolvedValue({ providers: [{ id: "openai-codex", name: "OpenAI Codex", flow: "device_code", cli_command: "codex login --device-auth", docs_url: "https://developers.openai.com/", status: { logged_in: true } }] });
    apiMocks.getArcenalConfiguration.mockResolvedValue({ ...CONFIGURATION, config: { ...CONFIGURATION.config, providers: { "openai-codex": { enabled: true } } } });
    render(<ArcenalSettingsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Fournisseurs IA" }));

    const card = (await screen.findByRole("heading", { name: "OpenAI Codex" })).closest("article") as HTMLElement;
    expect(within(card).getByText("Configuré")).toBeTruthy();
    fireEvent.click(within(card).getByRole("button", { name: "Déconnecter Codex" }));

    await waitFor(() => expect(apiMocks.disconnectOAuthProvider).toHaveBeenCalledWith("openai-codex"));
    expect(apiMocks.saveArcenalConfiguration).toHaveBeenCalledWith({ providers: { "openai-codex": { enabled: false } } });
  });

  it("finalise une authentification Codex avant de l’annoncer configurée", async () => {
    apiMocks.getOAuthProviders.mockResolvedValue({ providers: [{ id: "openai-codex", name: "OpenAI Codex", flow: "device_code", cli_command: "codex login --device-auth", docs_url: "https://developers.openai.com/", status: { logged_in: true } }] });
    render(<ArcenalSettingsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Fournisseurs IA" }));

    expect(await screen.findByText("À finaliser")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Finaliser la connexion Codex" }));

    await waitFor(() => expect(apiMocks.syncArcenalCodexProvider).toHaveBeenCalledOnce());
    expect(apiMocks.saveArcenalConfiguration).toHaveBeenCalledWith({ providers: { "openai-codex": { enabled: true } } });
    expect(await screen.findByText("Codex est connecté et ses modèles peuvent être attribués aux agents.")).toBeTruthy();
  });

  it("conserve Codex à finaliser si le catalogue des modèles est indisponible", async () => {
    apiMocks.getOAuthProviders.mockResolvedValue({ providers: [{ id: "openai-codex", name: "OpenAI Codex", flow: "device_code", cli_command: "codex login --device-auth", docs_url: "https://developers.openai.com/", status: { logged_in: true } }] });
    apiMocks.syncArcenalCodexProvider.mockRejectedValue(new Error("Catalogue Codex indisponible"));
    render(<ArcenalSettingsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Fournisseurs IA" }));
    fireEvent.click(await screen.findByRole("button", { name: "Finaliser la connexion Codex" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Catalogue Codex indisponible");
    expect(apiMocks.saveArcenalConfiguration).not.toHaveBeenCalled();
    expect(screen.getByText("À finaliser")).toBeTruthy();
  });

  it("enregistre uniquement la connexion du fournisseur", async () => {
    render(<ArcenalSettingsPage />);
    const card = await geminiCard();
    fireEvent.click(within(card).getByRole("button", { name: "Mettre à jour" }));
    await waitFor(() => expect(apiMocks.saveArcenalConfiguration).toHaveBeenCalledWith({
      providers: { gemini: { base_url: "https://generativelanguage.googleapis.com/v1beta", enabled: true } },
    }));
    expect(within(card).queryByLabelText("Modèle principal")).toBeNull();
  });

  it("affiche le catalogue comme une information attribuable aux agents", async () => {
    render(<ArcenalSettingsPage />);
    const card = await geminiCard();
    expect(within(card).getByText("Les modèles sont attribués dans le harnais de chaque agent.")).toBeTruthy();
    expect(within(card).getByText("1 modèle disponible")).toBeTruthy();
  });

  it("propage l’échec de la connexion sans annoncer une disponibilité", async () => {
    apiMocks.saveArcenalConfiguration.mockRejectedValue(new Error("Connexion indisponible"));
    render(<ArcenalSettingsPage />);
    const card = await geminiCard();
    fireEvent.click(within(card).getByRole("button", { name: "Mettre à jour" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Connexion indisponible");
    expect(screen.queryByText("Google Gemini est disponible pour ARC.")).toBeNull();
  });
});
