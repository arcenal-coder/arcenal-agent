import { useEffect, useState, type ReactElement } from "react";
import { Building2, Save, Server } from "lucide-react";
import { api, type ArcenalSystemOverview } from "@/lib/api";
import { generalSettingsConfig, generalSettingsFromConfig, isArcenalSystemOverview, isValidNotificationEmail, type ArcenalGeneralSettings } from "@/lib/arcenal-product-settings";

interface ArcenalGeneralSettingsProps {
  config: Record<string, unknown>;
  onReload: () => Promise<void>;
}

export function ArcenalGeneralSettingsPanel({ config, onReload }: ArcenalGeneralSettingsProps): ReactElement {
  const [settings, setSettings] = useState(() => generalSettingsFromConfig(config));
  const [overview, setOverview] = useState<ArcenalSystemOverview | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { void loadOverview(setOverview, setStatus); }, []);
  const save = (): void => { void saveGeneral(settings, setBusy, setStatus, onReload); };
  return <section className="arc-settings-section"><PanelHeading /><GeneralForm settings={settings} setSettings={setSettings} /><SystemIdentity overview={overview} />{status && <p className="arc-settings-status" role="status">{status}</p>}<button className="arc-primary-button" disabled={busy} onClick={save} type="button"><Save aria-hidden />{busy ? "Enregistrement…" : "Enregistrer les paramètres généraux"}</button></section>;
}

function PanelHeading(): ReactElement {
  return <div className="arc-settings-section-title"><span><Building2 /></span><div><small>Identité</small><h2>Paramètres généraux</h2><p>Définissez l’identité d’ARC et consultez les informations détectées sur le serveur.</p></div></div>;
}

function GeneralForm({ settings, setSettings }: { settings: ArcenalGeneralSettings; setSettings: (value: ArcenalGeneralSettings) => void }): ReactElement {
  const patch = (values: Partial<ArcenalGeneralSettings>): void => setSettings({ ...settings, ...values });
  return <div className="arc-general-grid"><TextField label="Nom de l’agent" value={settings.agentName} onChange={(agentName) => patch({ agentName })} /><TextField label="Organisation" value={settings.organizationName} onChange={(organizationName) => patch({ organizationName })} /><TextField label="Adresse de notification" value={settings.notificationEmail} type="email" placeholder="arc@domaine.tld" onChange={(notificationEmail) => patch({ notificationEmail })} /><TextField label="Fuseau horaire" value={settings.timezone} placeholder="Europe/Paris" onChange={(timezone) => patch({ timezone })} /><label className="arc-field"><span>Langue</span><select value={settings.language} onChange={(event) => patch({ language: event.target.value })}><option value="fr">Français</option><option value="en">English</option></select></label></div>;
}

function TextField({ label, value, onChange, placeholder = "", type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string }): ReactElement {
  return <label className="arc-field"><span>{label}</span><input type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>;
}

function SystemIdentity({ overview }: { overview: ArcenalSystemOverview | null }): ReactElement {
  if (!overview) return <div className="arc-system-identity" aria-busy="true"><Server aria-hidden /><span>Détection du serveur…</span></div>;
  const versions = overview.platform.versions;
  return <div className="arc-system-identity"><Server aria-hidden /><Identity label="Serveur" value={overview.platform.hostname} /><Identity label="Domaine principal" value={overview.platform.domain} /><Identity label="ARC" value={versions.arc} /><Identity label="Hermes" value={versions.hermes} /><Identity label="YunoHost" value={versions.yunohost} /><Identity label="Système" value={versions.debian} /></div>;
}

function Identity({ label, value }: { label: string; value: string }): ReactElement {
  return <dl><dt>{label}</dt><dd>{value}</dd></dl>;
}

async function loadOverview(setOverview: (value: ArcenalSystemOverview) => void, setStatus: (value: string) => void): Promise<void> {
  try {
    const response: unknown = await api.getArcenalSystemOverview();
    if (!isArcenalSystemOverview(response)) throw new Error("La réponse système d’ARC est incomplète.");
    setOverview(response);
  } catch (cause) {
    setStatus(errorMessage(cause, "Les informations du serveur sont indisponibles."));
  }
}

async function saveGeneral(settings: ArcenalGeneralSettings, setBusy: (value: boolean) => void, setStatus: (value: string) => void, reload: () => Promise<void>): Promise<void> {
  const validationError = validateGeneral(settings);
  if (validationError) return setStatus(validationError);
  setBusy(true);
  setStatus("");
  try {
    await api.saveConfig(generalSettingsConfig(settings));
    await reload();
    setStatus("Les paramètres généraux sont enregistrés.");
  } catch (cause) {
    setStatus(errorMessage(cause, "Enregistrement impossible."));
  } finally {
    setBusy(false);
  }
}

function validateGeneral(settings: ArcenalGeneralSettings): string {
  if (!settings.agentName.trim()) return "Le nom de l’agent est obligatoire.";
  if (!settings.organizationName.trim()) return "Le nom de l’organisation est obligatoire.";
  if (!settings.timezone.trim()) return "Le fuseau horaire est obligatoire.";
  if (!isValidNotificationEmail(settings.notificationEmail)) return "L’adresse de notification est invalide.";
  return "";
}

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}
