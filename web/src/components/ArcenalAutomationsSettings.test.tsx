// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ArcenalAutomationsSettingsPanel } from "./ArcenalAutomationsSettings";

const apiMocks = vi.hoisted(() => ({ getArcenalAutomations: vi.fn(), transitionArcenalWorkflow: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: apiMocks }));

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getArcenalAutomations.mockResolvedValue({ workflows: [{ id: "demo", name: "Rapport", description: "Construit un rapport stable.", version: 1, status: "testing", agent_id: "arc", trigger: "rapport", autonomy: "controlled", approved_by: null, executions: 0, exceptions: 0 }], candidates: [{ id: "candidate", name: "Processus ATS", description: "Candidat", observations: 4, confidence: 0.8, estimated_savings: 0, risk_level: "medium", reviewed: false }] });
  apiMocks.transitionArcenalWorkflow.mockResolvedValue({ status: "active" });
});
afterEach(cleanup);

describe("Automatisations gouvernées", () => {
  it("présente les workflows et candidats observés", async () => {
    render(<ArcenalAutomationsSettingsPanel />);
    expect(await screen.findByText("Rapport")).toBeTruthy();
    expect(screen.getByText("Processus ATS")).toBeTruthy();
  });

  it("exige une action humaine pour activer un workflow testé", async () => {
    render(<ArcenalAutomationsSettingsPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Approuver et activer" }));
    await waitFor(() => expect(apiMocks.transitionArcenalWorkflow).toHaveBeenCalledWith("demo", "active"));
  });
});
