export interface YunoHostBranding {
  logoUrl: string;
  title: string;
}

interface PortalSettings {
  portal_logo?: unknown;
  portal_title?: unknown;
}

type JsonFetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const SAFE_LOGO = /^[\w.-]+\.(?:jpe?g|png|svg)$/i;

export async function loadYunoHostBranding(fetcher: JsonFetcher, fallbackLogo: string): Promise<YunoHostBranding> {
  const response = await fetcher("/yunohost/portalapi/public", { credentials: "include" });
  if (!response.ok) throw new YunoHostBrandingError(`YunoHost a répondu ${response.status}.`);
  return resolveYunoHostBranding(await response.json() as PortalSettings, fallbackLogo);
}

export function resolveYunoHostBranding(settings: PortalSettings, fallbackLogo: string): YunoHostBranding {
  const logo = typeof settings.portal_logo === "string" ? settings.portal_logo.trim() : "";
  const title = typeof settings.portal_title === "string" && settings.portal_title.trim() ? settings.portal_title.trim() : "Votre organisation";
  if (!SAFE_LOGO.test(logo)) return { logoUrl: fallbackLogo, title };
  return { logoUrl: `/yunohost/sso/customassets/${encodeURIComponent(logo)}`, title };
}

export class YunoHostBrandingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "YunoHostBrandingError";
  }
}
