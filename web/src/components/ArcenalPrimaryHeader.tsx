import { Bot, BrainCircuit, MessageCircleMore, Settings } from "lucide-react";
import { useEffect, useState, type ReactElement } from "react";
import { NavLink } from "react-router";
import { HERMES_BASE_PATH } from "@/lib/api";
import { ARCENAL_LOGO_PATH } from "@/brand";
import { loadYunoHostBranding, type YunoHostBranding } from "@/lib/yunohost-branding";

const SECTIONS = [
  { path: "/chat", label: "ARC", description: "Administrer", icon: MessageCircleMore },
  { path: "/agents", label: "Agents", description: "Spécialiser", icon: Bot },
  { path: "/knowledge", label: "RAG & LDA", description: "Capitaliser", icon: BrainCircuit },
] as const;

export function ArcenalPrimaryHeader(): ReactElement {
  const fallbackLogo = `${HERMES_BASE_PATH}${ARCENAL_LOGO_PATH}`;
  const [branding, setBranding] = useState<YunoHostBranding>({ logoUrl: fallbackLogo, title: "ARCenal" });
  useEffect(() => {
    let active = true;
    void loadYunoHostBranding(window.fetch.bind(window), fallbackLogo)
      .then((value) => { if (active) setBranding(value); })
      .catch((cause: unknown) => {
        if (!active) return;
        console.warn("[ARCenal] Logo YunoHost indisponible, utilisation du logo de secours.", cause);
        setBranding({ logoUrl: fallbackLogo, title: "ARCenal" });
      });
    return () => { active = false; };
  }, [fallbackLogo]);
  return (
    <header className="arc-primary-header">
      <div className="arc-primary-brand">
        <img src={branding.logoUrl} alt={branding.title} />
      </div>
      <nav aria-label="Trois volets ARCenal" className="arc-primary-tabs">
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
