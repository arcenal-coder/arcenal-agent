import type { CSSProperties } from "react";
import { Link } from "react-router";
import { Activity, ArrowRight, Bot, Clock3, MessagesSquare, Radio, Send, ShieldCheck } from "lucide-react";
import { useSidebarStatus } from "@/hooks/useSidebarStatus";

const actions = [
  { title: "Lancer une mission", description: "Confiez une tâche à votre agent et suivez son exécution.", path: "/chat", icon: Bot, accent: "var(--arc-ink)" },
  { title: "Suivre l’activité", description: "Consultez les sessions, résultats et historiques de travail.", path: "/sessions", icon: MessagesSquare, accent: "var(--arc-prussian)" },
  { title: "Automatiser", description: "Planifiez les opérations récurrentes de votre organisation.", path: "/cron", icon: Clock3, accent: "var(--arc-brass)" },
  { title: "Connecter vos canaux", description: "Reliez ARCenal aux outils utilisés par vos équipes.", path: "/channels", icon: Radio, accent: "var(--arc-teal)" },
] as const;

export default function ControlCenterPage() {
  const status = useSidebarStatus();
  const operational = status !== null;
  const gatewayActive = status?.gateway_running === true;

  return (
    <main className="arcenal-board" aria-labelledby="arcenal-welcome-title">
      <section className="arcenal-welcome">
        <p className="arcenal-eyebrow">Votre centre de contrôle</p>
        <h1 id="arcenal-welcome-title">Bonjour, que souhaitez-vous accomplir&nbsp;?</h1>
        <p className="arcenal-intro">Pilotez vos agents, automatisez les opérations et gardez la maîtrise de votre environnement depuis un espace souverain.</p>
      </section>

      <Link to="/chat" className="arcenal-hero-command">
        <div>
          <span className="arcenal-command-kicker">Commande centrale</span>
          <strong>Confiez une mission à ARCenal</strong>
          <span className="arcenal-command-prompt">Décrivez votre objectif, l’agent organise la suite.</span>
        </div>
        <span className="arcenal-send" aria-hidden><Send /></span>
      </Link>

      <section className="arcenal-status-grid" aria-label="État de la plateforme">
        <StatusCard label="Plateforme" value={operational ? "Opérationnelle" : "Vérification…"} detail={status?.version ? `Version ${status.version}` : "Connexion au service"} healthy={operational} icon={Activity} />
        <StatusCard label="Agent" value={gatewayActive ? "Actif" : "Prêt à démarrer"} detail={`${status?.active_sessions ?? 0} session(s) active(s)`} healthy={gatewayActive} icon={Bot} />
        <StatusCard label="Environnement" value="Privé et sécurisé" detail="Hébergé sur votre infrastructure" healthy icon={ShieldCheck} />
      </section>

      <section aria-labelledby="arcenal-actions-title">
        <div className="arcenal-section-heading">
          <span aria-hidden />
          <div><p>Actions rapides</p><h2 id="arcenal-actions-title">Votre espace de pilotage</h2></div>
        </div>
        <div className="arcenal-action-grid">
          {actions.map(({ title, description, path, icon: Icon, accent }) => (
            <Link key={path} to={path} className="arcenal-action-card" style={{ "--arc-card-accent": accent } as CSSProperties}>
              <span className="arcenal-action-icon"><Icon aria-hidden /></span>
              <span className="arcenal-action-copy"><strong>{title}</strong><small>{description}</small></span>
              <ArrowRight aria-hidden className="arcenal-action-arrow" />
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

function StatusCard({ label, value, detail, healthy, icon: Icon }: { label: string; value: string; detail: string; healthy: boolean; icon: typeof Activity }) {
  return (
    <article className="arcenal-status-card">
      <div><p>{label}</p><strong>{value}</strong><small>{detail}</small></div>
      <span className={healthy ? "is-healthy" : "is-pending"}><Icon aria-hidden /></span>
    </article>
  );
}
