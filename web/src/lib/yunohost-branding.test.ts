import { describe, expect, it, vi } from "vitest";
import { loadYunoHostBranding, resolveYunoHostBranding, YunoHostBrandingError } from "./yunohost-branding";

describe("personnalisation YunoHost", () => {
  it("utilise le logo de l’organisation", () => {
    expect(resolveYunoHostBranding({ portal_logo: "onyx.svg", portal_title: "ONYX" }, "/arcenal.png"))
      .toEqual({ logoUrl: "/yunohost/sso/customassets/onyx.svg", title: "ONYX" });
  });

  it("conserve le logo ARCenal sans personnalisation", () => {
    expect(resolveYunoHostBranding({}, "/arcenal.png").logoUrl).toBe("/arcenal.png");
  });

  it("rejette un chemin de logo dangereux", () => {
    expect(resolveYunoHostBranding({ portal_logo: "../secret.svg" }, "/arcenal.png").logoUrl).toBe("/arcenal.png");
  });

  it("signale une API YunoHost indisponible", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    await expect(loadYunoHostBranding(fetcher, "/arcenal.png")).rejects.toBeInstanceOf(YunoHostBrandingError);
  });
});
