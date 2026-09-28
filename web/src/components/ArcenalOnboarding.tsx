import { Bot, CheckCircle2, CircleAlert, LoaderCircle, Stethoscope, X } from "lucide-react";
import { useCallback, useEffect, useState, type ReactElement } from "react";
import { api, type ArcenalProviderStatusesResponse, type ArcenalSecurityOverview, type ArcenalSystemOverview } from "@/lib/api";
import { isProviderStatusesResponse } from "@/lib/arcenal-provider-status";
import { isArcenalSecurityOverview } from "@/lib/arcenal-security";
import { onboardingChecks, onboardingCompleted, requiredChecksPass, type ArcenalOnboardingCheck } from "@/lib/arcenal-onboarding";
import { isArcenalSystemOverview } from "@/lib/arcenal-product-settings";

interface OnboardingState {
  busy: boolean;
  checks: ArcenalOnboardingCheck[];
  error: string;
  hidden: boolean;
  needed: boolean;
}

const SESSION_KEY = "arcenal-onboarding-deferred";
const INITIAL: OnboardingState = { busy: true, checks: [], error: "", hidden: false, needed: false };

export function ArcenalOnboarding(): ReactElement | null {
  const { state, setState, reload } = useOnboardingState();
  const diagnose = (): void => { void runDiagnosis(setState, reload); };
  const complete = (): void => { void completeOnboarding(setState); };
  const defer = (): void => { window.sessionStorage.setItem(SESSION_KEY, "true"); setState((current) => ({ ...current, hidden: true })); };
  if (state.hidden || !state.needed) return null;
  return <div className="arc-onboarding" role="dialog" aria-modal="true" aria-labelledby="arc-onboarding-title"><section><button aria-label="Continuer plus tard" className="arc-onboarding-close" onClick={defer} type="button"><X /></button><header><span><Bot /></span><small>Bienvenue dans ARCenal Système</small><h1 id="arc-onboarding-title">Initialisons ARC, votre architecte système</h1><p>Cette vérification confirme l’identité administrateur, les droits du broker et l’état du serveur sans exposer de secret.</p></header>{state.error && <p className="arc-alert arc-alert-error">{state.error}</p>}<OnboardingChecks busy={state.busy} checks={state.checks} /><footer><button className="arc-secondary-button" disabled={state.busy} onClick={diagnose} type="button"><Stethoscope /> Relancer le diagnostic</button><button className="arc-primary-button" disabled={state.busy || !requiredChecksPass(state.checks)} onClick={complete} type="button">Terminer l’initialisation</button></footer></section></div>;
}

function useOnboardingState(): { state: OnboardingState; setState: React.Dispatch<React.SetStateAction<OnboardingState>>; reload: () => Promise<void> } {
  const [state, setState] = useState<OnboardingState>(INITIAL);
  const reload = useCallback(async (): Promise<void> => {
    if (window.sessionStorage.getItem(SESSION_KEY) === "true") return setState((current) => ({ ...current, busy: false, hidden: true }));
    setState((current) => ({ ...current, busy: true, error: "" }));
    try {
      const config = await api.getConfig();
      if (onboardingCompleted(config)) return setState((current) => ({ ...current, busy: false, needed: false }));
      const values = await loadOnboardingValues();
      setState((current) => ({ ...current, busy: false, checks: onboardingChecks(...values), needed: true }));
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: message(cause), needed: true }));
    }
  }, []);
  useEffect(() => { void Promise.resolve().then(reload); }, [reload]);
  return { state, setState, reload };
}

async function loadOnboardingValues(): Promise<[ArcenalSecurityOverview, ArcenalSystemOverview, ArcenalProviderStatusesResponse]> {
  const [security, system, providers] = await Promise.all([api.getArcenalSecurityOverview(), api.getArcenalSystemOverview(), api.getArcenalProviderStatuses()]);
  if (!isArcenalSecurityOverview(security)) throw new Error("Le contrôle d’identité ARC est incomplet.");
  if (!isArcenalSystemOverview(system)) throw new Error("L’état YunoHost est incomplet.");
  if (!isProviderStatusesResponse(providers)) throw new Error("L’état des fournisseurs IA est incomplet.");
  return [security, system, providers];
}

function OnboardingChecks({ busy, checks }: { busy: boolean; checks: ArcenalOnboardingCheck[] }): ReactElement {
  if (busy) return <div className="arc-onboarding-loading"><LoaderCircle className="arc-spin" /> Vérification en cours…</div>;
  return <div className="arc-onboarding-checks">{checks.map((check) => <article data-ok={check.ok} key={check.id}>{check.ok ? <CheckCircle2 /> : <CircleAlert />}<span><strong>{check.label}</strong><small>{check.detail}</small></span><em>{check.ok ? "Prêt" : check.required ? "À corriger" : "Optionnel"}</em></article>)}</div>;
}

async function runDiagnosis(setState: SetOnboardingState, reload: () => Promise<void>): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "" }));
  try {
    await api.prepareArcenalAction("yunohost.diagnosis.refresh", null);
    await api.executeArcenalAction("yunohost.diagnosis.refresh", null);
    await reload();
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: message(cause) }));
  }
}

async function completeOnboarding(setState: SetOnboardingState): Promise<void> {
  setState((current) => ({ ...current, busy: true, error: "" }));
  try {
    await api.saveConfig({ arcenal: { onboarding: { completed: true, completed_at: new Date().toISOString(), version: 1 } } });
    setState((current) => ({ ...current, busy: false, hidden: true, needed: false }));
  } catch (cause) {
    setState((current) => ({ ...current, busy: false, error: message(cause) }));
  }
}

function message(cause: unknown): string {
  return cause instanceof Error ? cause.message : "L’initialisation d’ARC est indisponible.";
}

type SetOnboardingState = React.Dispatch<React.SetStateAction<OnboardingState>>;
