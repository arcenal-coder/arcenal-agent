// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { EnterpriseMemoryEntry } from "@/lib/api";
import { ArcenalMemorySettingsPanel } from "./ArcenalMemorySettings";

const apiMocks = vi.hoisted(() => ({
  createEnterpriseMemory: vi.fn(), correctEnterpriseMemory: vi.fn(), deleteEnterpriseMemory: vi.fn(),
  getEnterpriseMemories: vi.fn(), getEnterpriseMemory: vi.fn(), getEnterpriseMemoryMetrics: vi.fn(),
  transitionEnterpriseMemory: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMocks }));

const ENTRY: EnterpriseMemoryEntry = {
  allowed_agents: [], allowed_applications: [], allowed_users: [], confidentiality: "internal",
  confidence: 1, content: "SilverBullet est retenu comme wiki léger.", created_at: "2026-09-30T08:00:00Z",
  created_by: "admin", decision_context: "Wiki léger", decision_maker: "Direction",
  decision_reason: "Simplicité", expires_at: null, id: "memory-1", knowledge_scopes: ["company"],
  memory_type: "decision", official_reference: null, person: null, person_role: null,
  person_service: null, preference_context: null, preference_owner: null, preference_scope: null,
  project: "ARCenal", project_status: null,
  provenance: { agent_id: null, application_id: null, author: "Direction", recorded_at: "2026-09-30T08:00:00Z", request_id: null, source_id: "comite-1", source_type: "manual" },
  relations: [], responsibilities: [], retention_mode: "permanent", review_date: null,
  rule_kind: null, status: "active", summary: "Choix de SilverBullet", updated_at: "2026-09-30T08:00:00Z", version: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getEnterpriseMemories.mockResolvedValue({ entries: [ENTRY] });
  apiMocks.getEnterpriseMemoryMetrics.mockResolvedValue({ active: 1, archived: 0, by_scope: { company: 1 }, by_type: { decision: 1 }, deleted: 0, expired: 0, pending_review: 0, total: 1, used_by_rag: 2 });
  apiMocks.getEnterpriseMemory.mockResolvedValue({ entry: ENTRY, history: [] });
  apiMocks.transitionEnterpriseMemory.mockResolvedValue({ entry: ENTRY });
  apiMocks.deleteEnterpriseMemory.mockResolvedValue({ deleted: true, physical: false });
});

afterEach(cleanup);

describe("Mémoire d’entreprise ARCenal", () => {
  it("affiche la liste, les métriques et applique les filtres", async () => {
    render(<ArcenalMemorySettingsPanel />);
    expect(await screen.findByText("Choix de SilverBullet")).toBeTruthy();
    expect(screen.getByText("Injectées dans le RAG")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Filtrer par type"), { target: { value: "decision" } });
    fireEvent.click(screen.getByRole("button", { name: "Filtrer" }));
    await waitFor(() => expect(apiMocks.getEnterpriseMemories).toHaveBeenLastCalledWith(expect.objectContaining({ memory_type: "decision" })));
  });

  it("crée une mémoire gouvernée depuis le formulaire", async () => {
    apiMocks.createEnterpriseMemory.mockResolvedValue({ entry: ENTRY });
    render(<ArcenalMemorySettingsPanel />);
    await screen.findByText("Choix de SilverBullet");
    fireEvent.change(screen.getByLabelText("Résumé"), { target: { value: "Outil de paie" } });
    fireEvent.change(screen.getByLabelText("Contenu"), { target: { value: "ONYX utilise SILAE." } });
    fireEvent.click(screen.getByRole("button", { name: "Créer la mémoire" }));
    await waitFor(() => expect(apiMocks.createEnterpriseMemory).toHaveBeenCalledWith(
      expect.objectContaining({ content: "ONYX utilise SILAE.", source_id: "saisie-administrateur", summary: "Outil de paie" }),
    ));
  });

  it("ouvre la fiche et archive avec un motif", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("Décision remplacée");
    render(<ArcenalMemorySettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Voir Choix de SilverBullet" }));
    expect(await screen.findByText("Historique de correction")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Archiver" }));
    await waitFor(() => expect(apiMocks.transitionEnterpriseMemory).toHaveBeenCalledWith("memory-1", "archived", "Décision remplacée"));
  });

  it("corrige une mémoire avec un motif et conserve ses ACL", async () => {
    apiMocks.correctEnterpriseMemory.mockResolvedValue({ entry: ENTRY });
    render(<ArcenalMemorySettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Modifier Choix de SilverBullet" }));
    fireEvent.change(screen.getByLabelText("Applications autorisées"), { target: { value: "arcenal-ats" } });
    fireEvent.change(screen.getByLabelText("Raison de la correction"), { target: { value: "Décision confirmée" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer la correction" }));
    await waitFor(() => expect(apiMocks.correctEnterpriseMemory).toHaveBeenCalledWith(
      "memory-1",
      expect.objectContaining({ allowed_applications: ["arcenal-ats"], reason: "Décision confirmée" }),
    ));
  });

  it("confirme et exécute le droit à l’oubli", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "prompt").mockReturnValue("Demande de la personne concernée");
    render(<ArcenalMemorySettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Voir Choix de SilverBullet" }));
    fireEvent.click(await screen.findByRole("button", { name: "Droit à l’oubli" }));
    await waitFor(() => expect(apiMocks.deleteEnterpriseMemory).toHaveBeenCalledWith(
      "memory-1", true, "Demande de la personne concernée",
    ));
  });

  it("présente clairement un refus de permission", async () => {
    apiMocks.getEnterpriseMemories.mockRejectedValue(new Error("Authentification administrateur requise."));
    render(<ArcenalMemorySettingsPanel />);
    expect((await screen.findByRole("alert")).textContent).toContain("Authentification administrateur requise.");
  });
});
