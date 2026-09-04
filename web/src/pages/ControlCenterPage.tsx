import { Link } from "react-router";
import {
  Activity,
  ArrowRight,
  Bot,
  Clock3,
  MessagesSquare,
  Radio,
  ShieldCheck,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { useSidebarStatus } from "@/hooks/useSidebarStatus";
import { ARCENAL_BRAND, ARCENAL_LOGO_PATH, HERMES_CREDIT } from "@/brand";
import { HERMES_BASE_PATH } from "@/lib/api";

const logoUrl = `${HERMES_BASE_PATH}${ARCENAL_LOGO_PATH}`;

const actions = [
  {
    title: "Lancer une mission",
    description: "Confiez une tâche à votre agent et suivez son exécution.",
    path: "/chat",
    icon: Bot,
  },
  {
    title: "Suivre l'activité",
    description: "Consultez les sessions, résultats et historiques de travail.",
    path: "/sessions",
    icon: MessagesSquare,
  },
  {
    title: "Automatiser",
    description: "Planifiez les opérations récurrentes de votre organisation.",
    path: "/cron",
    icon: Clock3,
  },
  {
    title: "Connecter vos canaux",
    description: "Reliez ARCenal aux outils utilisés par vos équipes.",
    path: "/channels",
    icon: Radio,
  },
] as const;

export default function ControlCenterPage() {
  const status = useSidebarStatus();
  const operational = status !== null;
  const gatewayActive = status?.gateway_running === true;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <section className="relative overflow-hidden border border-current/15 bg-background-surface p-6 sm:p-8">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-midground/10 blur-3xl" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-5 flex items-center gap-4">
              <img src={logoUrl} alt={ARCENAL_BRAND} className="h-20 w-auto object-contain" />
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-text-tertiary">
                  Centre de contrôle IA
                </p>
                <p className="mt-1 text-xs text-text-tertiary">{HERMES_CREDIT}</p>
              </div>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Pilotez vos opérations avec ARCenal
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-text-secondary sm:text-base">
              Un espace souverain pour orchestrer les agents, automatiser les processus
              et garder la maîtrise des données de votre organisation.
            </p>
          </div>

          <Link
            to="/chat"
            className="inline-flex w-full items-center justify-center bg-midground px-5 py-3 text-sm font-medium text-background-base transition-opacity hover:opacity-90 sm:w-auto"
          >
            Démarrer une mission
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatusCard
          label="Plateforme"
          value={operational ? "Opérationnelle" : "Vérification…"}
          detail={status?.version ? `Version ${status.version}` : "Connexion au service"}
          healthy={operational}
          icon={Activity}
        />
        <StatusCard
          label="Agent"
          value={gatewayActive ? "Actif" : "Prêt à démarrer"}
          detail={`${status?.active_sessions ?? 0} session(s) active(s)`}
          healthy={gatewayActive}
          icon={Bot}
        />
        <StatusCard
          label="Environnement"
          value="Privé et sécurisé"
          detail="Hébergé sur votre infrastructure"
          healthy
          icon={ShieldCheck}
        />
      </section>

      <section>
        <div className="mb-4">
          <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary">Actions rapides</p>
          <h2 className="mt-1 text-xl font-semibold">Votre espace de pilotage</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {actions.map(({ title, description, path, icon: Icon }) => (
            <Link key={path} to={path} className="group focus-visible:outline-none">
              <Card className="h-full transition-colors group-hover:border-midground/50">
                <CardHeader className="flex flex-row items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center bg-midground/10 text-midground">
                      <Icon className="h-5 w-5" />
                    </span>
                    <CardTitle className="text-base">{title}</CardTitle>
                  </div>
                  <ArrowRight className="h-4 w-4 text-text-tertiary transition-transform group-hover:translate-x-1" />
                </CardHeader>
                <CardContent className="text-sm leading-6 text-text-secondary">
                  {description}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatusCard({
  label,
  value,
  detail,
  healthy,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  healthy: boolean;
  icon: typeof Activity;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-text-tertiary">{label}</p>
          <p className="mt-2 font-medium">{value}</p>
          <p className="mt-1 text-xs text-text-secondary">{detail}</p>
        </div>
        <span className={healthy ? "text-emerald-500" : "text-amber-500"}>
          <Icon className="h-5 w-5" />
        </span>
      </CardContent>
    </Card>
  );
}
