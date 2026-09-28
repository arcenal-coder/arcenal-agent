import { describe, expect, it } from "vitest";
import {
  appearanceSettingsConfig,
  appearanceSettingsFromConfig,
  applyAppearance,
  generalSettingsConfig,
  generalSettingsFromConfig,
  isCssHexColor,
  isArcenalSystemOverview,
  isValidBrandUrl,
  isValidNotificationEmail,
  productBranding,
} from "./arcenal-product-settings";

describe("paramètres produit ARCenal", () => {
  it("lit les réglages Général et Apparence persistés", () => {
    const config = { arcenal: { general: { agent_name: "Athéna", organization_name: "Onyx" }, appearance: { accent_color: "#112233", logo_url: "https://example.test/logo.png" } } };
    expect(generalSettingsFromConfig(config)).toMatchObject({ agentName: "Athéna", organizationName: "Onyx" });
    expect(appearanceSettingsFromConfig(config)).toMatchObject({ accentColor: "#112233", logoUrl: "https://example.test/logo.png" });
  });

  it("applique les valeurs sûres par défaut aux configurations vides", () => {
    expect(generalSettingsFromConfig({})).toMatchObject({ agentName: "ARC", language: "fr" });
    expect(appearanceSettingsFromConfig({}).accentColor).toBe("#9F3434");
  });

  it("rejette les couleurs et adresses dangereuses", () => {
    expect(isCssHexColor("red")).toBe(false);
    expect(isValidBrandUrl("javascript:alert(1)")).toBe(false);
    expect(isValidNotificationEmail("administrateur")).toBe(false);
    expect(appearanceSettingsFromConfig({ arcenal: { appearance: { accent_color: "red", logo_url: "javascript:alert(1)" } } })).toMatchObject({ accentColor: "#9F3434", logoUrl: "" });
  });

  it("accepte une adresse de notification vide ou correctement formée", () => {
    expect(isValidNotificationEmail(" ")).toBe(true);
    expect(isValidNotificationEmail("arc@example.test")).toBe(true);
  });

  it("accepte uniquement les ressources graphiques internes bornées", () => {
    expect(isValidBrandUrl("/arcenal/api/plugins/arcenal-supervisor/branding/assets/logo?v=12")).toBe(true);
    expect(isValidBrandUrl("/arcenal/api/plugins/arcenal-supervisor/branding/assets/../../secret")).toBe(false);
  });

  it("refuse une réponse système incomplète provenant d’une ancienne API", () => {
    expect(isArcenalSystemOverview({})).toBe(false);
    expect(isArcenalSystemOverview({ platform: { hostname: "arc", domain: "arc.test", versions: { arc: "1", hermes: "1", yunohost: "12", debian: "12" } } })).toBe(true);
  });

  it("prépare des fragments de configuration sans conserver les espaces parasites", () => {
    const general = generalSettingsFromConfig({});
    const appearance = appearanceSettingsFromConfig({});
    expect(generalSettingsConfig({ ...general, agentName: "  ARC  " })).toMatchObject({ arcenal: { general: { agent_name: "ARC" } } });
    expect(appearanceSettingsConfig({ ...appearance, logoUrl: "  https://example.test/logo.png  " })).toMatchObject({ arcenal: { appearance: { logo_url: "https://example.test/logo.png" } } });
  });

  it("applique les couleurs au conteneur produit", () => {
    const properties = new Map<string, string>();
    const root = { style: { setProperty: (name: string, value: string): void => { properties.set(name, value); } } };
    applyAppearance({ ...appearanceSettingsFromConfig({}), accentColor: "#123456" }, root);
    expect(properties.get("--arc-wine")).toBe("#123456");
    expect(properties.get("--arc-action")).toBe("#D95A35");
  });

  it("conserve l'identité de secours lorsque la configuration est incomplète", () => {
    const fallback = { faviconUrl: "/favicon.svg", logoUrl: "/logo.svg", title: "ARCenal" };
    expect(productBranding({}, fallback)).toEqual(fallback);
  });
});
