// @vitest-environment jsdom
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OAuthLoginModal } from "./OAuthLoginModal";

const apiMocks = vi.hoisted(() => ({
  cancelOAuthSession: vi.fn(),
  pollOAuthSession: vi.fn(),
  startOAuthLogin: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMocks }));

const PROVIDER = {
  cli_command: "hermes auth add openai-codex",
  docs_url: "https://developers.openai.com/",
  flow: "device_code" as const,
  id: "openai-codex",
  name: "OpenAI Codex",
  status: { logged_in: false },
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("open", vi.fn());
  apiMocks.startOAuthLogin.mockResolvedValue({ expires_in: 900, flow: "device_code", poll_interval: 2, session_id: "session-1", user_code: "CODE-123", verification_url: "https://auth.openai.com/device" });
  apiMocks.pollOAuthSession.mockResolvedValue({ status: "approved" });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

async function approveDevice(): Promise<void> {
  await act(async () => { await Promise.resolve(); });
  await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
}

describe("connexion OAuth par code d’appareil", () => {
  it("attend la finalisation ARC avant d’annoncer le succès", async () => {
    let resolveSync: (() => void) | undefined;
    const onSuccess = vi.fn(() => new Promise<void>((resolve) => { resolveSync = resolve; }));
    const onClose = vi.fn();
    const view = render(<OAuthLoginModal provider={PROVIDER} onClose={onClose} onError={vi.fn()} onSuccess={onSuccess} />);

    await approveDevice();
    expect(onSuccess).toHaveBeenCalledOnce();
    expect(onClose).not.toHaveBeenCalled();

    view.rerender(<OAuthLoginModal provider={PROVIDER} onClose={onClose} onError={vi.fn()} onSuccess={(message) => onSuccess(message)} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(onSuccess).toHaveBeenCalledOnce();

    await act(async () => { resolveSync?.(); await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1_500); });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("reste ouverte et affiche l’échec de synchronisation", async () => {
    const onClose = vi.fn();
    const onError = vi.fn();
    render(<OAuthLoginModal provider={PROVIDER} onClose={onClose} onError={onError} onSuccess={() => Promise.reject(new Error("Catalogue Codex indisponible"))} />);

    await approveDevice();
    expect(screen.getByText("Catalogue Codex indisponible")).toBeTruthy();
    expect(onError).toHaveBeenCalledWith("Catalogue Codex indisponible");
    expect(onClose).not.toHaveBeenCalled();
  });
});
