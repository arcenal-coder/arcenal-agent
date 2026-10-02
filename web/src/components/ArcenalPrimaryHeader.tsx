import { Bot, BrainCircuit, CalendarClock, MessageCircleMore, Settings } from "lucide-react";
import { useEffect, useState, type ReactElement } from "react";
import { NavLink } from "react-router";
import { api, HERMES_BASE_PATH } from "@/lib/api";
import { ARCENAL_LOGO_PATH } from "@/brand";
import { loadYunoHostBranding } from "@/lib/yunohost-branding";
import { ARCENAL_BRANDING_EVENT, appearanceSettingsFromConfig, applyAppearance, productBranding, type ArcenalBranding } from "@/lib/arcenal-product-settings";

const SECTIONS = [
  { path: "/chat", label: "ARC", description: "Administrer", icon: MessageCircleMore },
  { path: "/scheduled-tasks", label: "Tâches planifiées", description: "Automatiser", icon: CalendarClock },
  { path: "/agents", label: "Agents", description: "Spécialiser", icon: Bot },
  { path: "/knowledge", label: "RAG & LDA", description: "Capitaliser", icon: BrainCircuit },
] as const;

export function ArcenalPrimaryHeader(): ReactElement {
  const fallbackLogo = `${HERMES_BASE_PATH}${ARCENAL_LOGO_PATH}`;
  const [branding, setBranding] = useState<ArcenalBranding>({ faviconUrl: "", logoUrl: fallbackLogo, title: "ARCenal" });
  useEffect(() => {
    let active = true;
    const fallback = { faviconUrl: "", logoUrl: fallbackLogo, title: "ARCenal" };
    const refresh = (): void => { void loadProductBranding(fallback).then((value) => { if (active) setBranding(value); }); };
    refresh();
    window.addEventListener(ARCENAL_BRANDING_EVENT, refresh);
    return () => { active = false; window.removeEventListener(ARCENAL_BRANDING_EVENT, refresh); };
  }, [fallbackLogo]);
  return (
    <header className="arc-primary-header">
      <div className="arc-primary-brand">
        <img src={branding.logoUrl} alt={branding.title} />
      </div>
      <nav aria-label="Espaces ARCenal" className="arc-primary-tabs">
        {SECTIONS.map(({ path, label, description, icon: Icon }) => (
          <NavLink key={path} to={path} className="arc-primary-tab">
            <Icon aria-hidden />
            <span><strong>{label}</strong><small>{description}</small></span>
          </NavLink>
        ))}
      </nav>
      <div className="arc-header-meta">
        <NavLink to="/settings" className="arc-settings-link"><Settings aria-hidden /><span>Paramètres</span></NavLink>
        <span className="arc-engine-credit">by Hermes</span>
      </div>
    </header>
  );
}

async function loadProductBranding(fallback: ArcenalBranding): Promise<ArcenalBranding> {
  const [yunohost, config] = await Promise.all([
    loadYunoHostBranding(window.fetch.bind(window), fallback.logoUrl).catch(() => fallback),
    api.getArcenalConfiguration().then((response) => response.config).catch(() => ({})),
  ]);
  const branding = productBranding(config, { ...fallback, ...yunohost });
  applyAppearance(appearanceSettingsFromConfig(config), appearanceRoot());
  applyFavicon(branding.faviconUrl);
  return branding;
}

function appearanceRoot(): HTMLElement {
  return document.querySelector<HTMLElement>(".arcenal-shell") ?? document.documentElement;
}

function applyFavicon(url: string): void {
  const existing = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!url) {
    if (existing?.dataset.arcenalDefaultHref) existing.href = existing.dataset.arcenalDefaultHref;
    return;
  }
  const link = existing ?? document.createElement("link");
  if (existing && !link.dataset.arcenalDefaultHref) link.dataset.arcenalDefaultHref = link.href;
  link.rel = "icon";
  link.href = url;
  if (!existing) document.head.append(link);
}
