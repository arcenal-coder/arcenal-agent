import { Bot, BrainCircuit, MessageCircleMore, Settings } from "lucide-react";
import type { ReactElement } from "react";
import { NavLink } from "react-router";
import { HERMES_BASE_PATH } from "@/lib/api";
import { ARCENAL_LOGO_PATH } from "@/brand";

const SECTIONS = [
  { path: "/chat", label: "ARC", description: "Administrer", icon: MessageCircleMore },
  { path: "/agents", label: "Agents", description: "Spécialiser", icon: Bot },
  { path: "/knowledge", label: "RAG & LDA", description: "Capitaliser", icon: BrainCircuit },
] as const;

export function ArcenalPrimaryHeader(): ReactElement {
  const logo = `${HERMES_BASE_PATH}${ARCENAL_LOGO_PATH}`;
  return (
    <header className="arc-primary-header">
      <div className="arc-primary-brand">
        <img src={logo} alt="ARCenal" />
        <span><strong>ARC</strong><small>Architecte ARCenal Système</small></span>
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
        <span className="arc-engine-credit">Moteur <b>Hermes</b></span>
      </div>
    </header>
  );
}
