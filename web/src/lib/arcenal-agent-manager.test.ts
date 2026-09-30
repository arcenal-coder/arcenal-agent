import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchJSON } from "./api";
import { loadManagedAgents, updateManagedAgent } from "./arcenal-agent-manager";

vi.mock("./api", () => ({ fetchJSON: vi.fn() }));

describe("registre ARC Core", () => {
  beforeEach(() => vi.clearAllMocks());

  it("charge les agents gouvernés", async () => {
    vi.mocked(fetchJSON).mockResolvedValue({ agents: [{ id: "arc" }, { id: "ats" }] });
    await expect(loadManagedAgents()).resolves.toHaveLength(2);
  });

  it("persiste uniquement les réglages sûrs", async () => {
    vi.mocked(fetchJSON).mockResolvedValue({ id: "ats", enabled: false });
    await updateManagedAgent("ats", { autonomy_level: "controlled", enabled: false });
    expect(fetchJSON).toHaveBeenCalledWith(expect.stringContaining("/ats"), expect.objectContaining({ method: "PATCH" }));
  });
});
