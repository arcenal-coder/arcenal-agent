// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, fetchJSON, setManagementProfile } from "./api";

const reloadMocks = vi.hoisted(() => ({
  attemptDashboardTokenReloadOnce: vi.fn(() => false),
  clearDashboardTokenReloadAttempt: vi.fn(),
}));

vi.mock("./dashboard-auth-reload", () => ({
  attemptDashboardTokenReloadOnce: reloadMocks.attemptDashboardTokenReloadOnce,
  clearDashboardTokenReloadAttempt: reloadMocks.clearDashboardTokenReloadAttempt,
}));

const SESSION_HEADER = "X-Hermes-Session-Token";

beforeEach(() => {
  reloadMocks.attemptDashboardTokenReloadOnce.mockReset();
  reloadMocks.attemptDashboardTokenReloadOnce.mockReturnValue(false);
  reloadMocks.clearDashboardTokenReloadAttempt.mockReset();

  Object.defineProperty(window, "__HERMES_SESSION_TOKEN__", {
    configurable: true,
    value: "stale-token",
    writable: true,
  });
  Object.defineProperty(window, "__HERMES_AUTH_REQUIRED__", {
    configurable: true,
    value: false,
    writable: true,
  });
});

afterEach(() => {
  setManagementProfile("");
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function jsonFetchMock(body: unknown = { ok: true }) {
  return vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify(body), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
  );
}

describe("fetchJSON", () => {
  it("tries the one-shot reload path for loopback 401s", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        clone: () => ({
          json: async () => ({}),
        }),
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: async () => "Unauthorized",
      })),
    );
    reloadMocks.attemptDashboardTokenReloadOnce.mockReturnValue(true);

    const pending = fetchJSON("/api/status");
    await expect(Promise.race([pending, Promise.resolve("pending")])).resolves.toBe(
      "pending",
    );

    expect(reloadMocks.attemptDashboardTokenReloadOnce).toHaveBeenCalledTimes(1);
    expect(reloadMocks.clearDashboardTokenReloadAttempt).not.toHaveBeenCalled();
  });

  it("clears the reload latch after a successful response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        json: async () => ({ ok: true }),
        ok: true,
        status: 200,
      })),
    );

    await expect(fetchJSON("/api/status")).resolves.toEqual({ ok: true });

    expect(reloadMocks.clearDashboardTokenReloadAttempt).toHaveBeenCalledTimes(1);
  });
});

describe("api.getModelOptions", () => {
  it("requests a live model refresh when asked", async () => {
    vi.stubGlobal("window", {});

    const fetchMock = jsonFetchMock({ providers: [] });
    vi.stubGlobal("fetch", fetchMock);

    await api.getModelOptions({ refresh: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/model/options?refresh=1&include_unconfigured=1",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("keeps explicit profile scoping when refreshing", async () => {
    vi.stubGlobal("window", {});

    const fetchMock = jsonFetchMock({ providers: [] });
    vi.stubGlobal("fetch", fetchMock);

    await api.getModelOptions({ profile: "default", refresh: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/model/options?profile=default&refresh=1&include_unconfigured=1",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});

describe("api.testArcenalOpenRouter", () => {
  it("envoie la clé uniquement au test ARCenal demandé", async () => {
    const fetchMock = jsonFetchMock({ configured: true, connection: "connected" });
    vi.stubGlobal("fetch", fetchMock);

    await api.testArcenalOpenRouter("  sk-or-test  ");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/plugins/arcenal-supervisor/openrouter/test",
      expect.objectContaining({
        body: JSON.stringify({ api_key: "sk-or-test" }),
        method: "POST",
      }),
    );
  });

  it("demande au serveur de tester la clé déjà enregistrée", async () => {
    const fetchMock = jsonFetchMock({ configured: false, connection: "missing" });
    vi.stubGlobal("fetch", fetchMock);

    await api.testArcenalOpenRouter();

    const options = fetchMock.mock.calls[0][1] as RequestInit;
    expect(options.body).toBe(JSON.stringify({ api_key: null }));
  });
});

describe("api fichiers administrés ARCenal", () => {
  it("filtre le catalogue selon la catégorie demandée", async () => {
    const fetchMock = jsonFetchMock({ files: [] });
    vi.stubGlobal("fetch", fetchMock);

    await api.getArcenalManagedFiles("directive");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/plugins/arcenal-supervisor/managed-files?category=directive",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("enregistre uniquement le contenu du fichier sélectionné", async () => {
    const fetchMock = jsonFetchMock({ content: "# Contexte", file: {} });
    vi.stubGlobal("fetch", fetchMock);

    await api.saveArcenalManagedFile("context", "# Contexte");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/plugins/arcenal-supervisor/managed-files/context",
      expect.objectContaining({ body: JSON.stringify({ content: "# Contexte" }), method: "PUT" }),
    );
  });

  it("confirme explicitement la restauration d’une version", async () => {
    const fetchMock = jsonFetchMock({ content: "", file: {} });
    vi.stubGlobal("fetch", fetchMock);

    await api.restoreArcenalManagedFile("security", "20260928T120000000000Z");

    const options = fetchMock.mock.calls[0][1] as RequestInit;
    expect(options.body).toBe(JSON.stringify({ confirmed: true }));
    expect(options.method).toBe("POST");
  });
});

describe("api mémoire ARCenal", () => {
  it("encode la recherche sans l’injecter dans le chemin", async () => {
    const fetchMock = jsonFetchMock({ entries: [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.getArcenalMemoryEntries("projet & décisions");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/plugins/arcenal-supervisor/managed-files/memory/entries?query=projet%20%26%20d%C3%A9cisions",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("envoie une entrée structurée lors de sa création", async () => {
    const fetchMock = jsonFetchMock({ entry: { id: "1", title: "Décision", content: "Texte" } });
    vi.stubGlobal("fetch", fetchMock);
    await api.createArcenalMemoryEntry("Décision", "Texte");
    const options = fetchMock.mock.calls[0][1] as RequestInit;
    expect(options.body).toBe(JSON.stringify({ title: "Décision", content: "Texte" }));
    expect(options.method).toBe("POST");
  });

  it("confirme explicitement la suppression d’une entrée", async () => {
    const fetchMock = jsonFetchMock({ deleted: true });
    vi.stubGlobal("fetch", fetchMock);
    await api.deleteArcenalMemoryEntry("mémoire/1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/plugins/arcenal-supervisor/managed-files/memory/entries/m%C3%A9moire%2F1/delete",
      expect.objectContaining({ body: JSON.stringify({ confirmed: true }), method: "POST" }),
    );
  });
});

describe("api OAuth helpers", () => {
  it("starts OAuth login in gated mode without requiring an injected session token", async () => {
    vi.stubGlobal("window", { __HERMES_AUTH_REQUIRED__: true });
    const fetchMock = jsonFetchMock({
      flow: "device_code",
      session_id: "oauth-session",
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.startOAuthLogin("openai-codex");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/providers/oauth/openai-codex/start",
      expect.objectContaining({
        body: "{}",
        credentials: "include",
        method: "POST",
      }),
    );
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.has(SESSION_HEADER)).toBe(false);
  });

  it("still sends the injected session token for OAuth login in loopback mode", async () => {
    vi.stubGlobal("window", { __HERMES_SESSION_TOKEN__: "loopback-token" });
    const fetchMock = jsonFetchMock({
      flow: "device_code",
      session_id: "oauth-session",
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.startOAuthLogin("openai-codex");

    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get(SESSION_HEADER)).toBe("loopback-token");
  });

  it("runs provider auth mutations in gated mode via cookie auth", async () => {
    vi.stubGlobal("window", { __HERMES_AUTH_REQUIRED__: true });
    const fetchMock = jsonFetchMock({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await api.disconnectOAuthProvider("anthropic");
    await api.submitOAuthCode("anthropic", "oauth-session", "code-123");
    await api.cancelOAuthSession("oauth-session");
    await api.revealEnvVar("OPENAI_API_KEY");

    for (const call of fetchMock.mock.calls) {
      const init = call[1] as RequestInit;
      expect(init.credentials).toBe("include");
      expect((init.headers as Headers).has(SESSION_HEADER)).toBe(false);
    }
  });

  it("keeps every OAuth operation on the selected management profile", async () => {
    vi.stubGlobal("window", {});
    const fetchMock = jsonFetchMock({
      flow: "device_code",
      session_id: "oauth-session",
    });
    vi.stubGlobal("fetch", fetchMock);
    setManagementProfile("worker");

    await api.getOAuthProviders();
    await api.disconnectOAuthProvider("anthropic");
    await api.startOAuthLogin("openai-codex");
    await api.submitOAuthCode("anthropic", "oauth-session", "code-123");
    await api.pollOAuthSession("anthropic", "oauth-session");
    await api.cancelOAuthSession("oauth-session");

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/providers/oauth?profile=worker",
      "/api/providers/oauth/anthropic?profile=worker",
      "/api/providers/oauth/openai-codex/start?profile=worker",
      "/api/providers/oauth/anthropic/submit?profile=worker",
      "/api/providers/oauth/anthropic/poll/oauth-session?profile=worker",
      "/api/providers/oauth/sessions/oauth-session?profile=worker",
    ]);
  });
});
