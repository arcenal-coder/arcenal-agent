import { useEffect, useState, type ReactElement } from "react";
import { Image, Monitor, Moon, Palette, Save, Sun } from "lucide-react";
import { api } from "@/lib/api";
import { useArcColorMode, type ArcColorMode } from "@/lib/arcenal-color-mode";
import { ARCENAL_BRANDING_EVENT, appearanceSettingsConfig, appearanceSettingsFromConfig, applyAppearance, isValidBrandUrl, type ArcenalAppearanceSettings } from "@/lib/arcenal-product-settings";

interface ArcenalAppearanceSettingsProps {
  config: Record<string, unknown>;
  onReload: () => Promise<void>;
}

export function ArcenalAppearanceSettingsPanel({ config, onReload }: ArcenalAppearanceSettingsProps): ReactElement {
  const { mode, setMode } = useArcColorMode();
  const [settings, setSettings] = useState(() => appearanceSettingsFromConfig(config));
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => applyAppearance(settings, appearanceRoot()), [settings]);
  const save = (): void => { void saveAppearance(settings, setBusy, setStatus, onReload); };
  return <section className="arc-settings-section"><PanelHeading /><ThemeModes mode={mode} setMode={setMode} /><AppearanceForm settings={settings} setSettings={setSettings} /><AppearancePreview settings={settings} />{status && <p className="arc-settings-status" role="status">{status}</p>}<button className="arc-primary-button" disabled={busy} onClick={save} type="button"><Save aria-hidden />{busy ? "Enregistrement…" : "Enregistrer l’apparence"}</button></section>;
}

function appearanceRoot(): HTMLElement {
  return document.querySelector<HTMLElement>(".arcenal-shell") ?? document.documentElement;
}

function PanelHeading(): ReactElement {
  return <div className="arc-settings-section-title"><span><Palette /></span><div><small>Personnalisation</small><h2>Apparence d’ARC</h2><p>Le logo YunoHost reste utilisé par défaut. Toute personnalisation est prévisualisée avant enregistrement.</p></div></div>;
}

function ThemeModes({ mode, setMode }: { mode: ArcColorMode; setMode: (mode: ArcColorMode) => void }): ReactElement {
  const options: Array<{ icon: ReactElement; id: ArcColorMode; label: string }> = [{ icon: <Sun />, id: "light", label: "Clair" }, { icon: <Moon />, id: "dark", label: "Sombre" }, { icon: <Monitor />, id: "system", label: "Système" }];
  return <div className="arc-appearance"><strong>Thème</strong><div>{options.map((option) => <button aria-pressed={mode === option.id} key={option.id} onClick={() => setMode(option.id)} type="button">{option.icon}<span>{option.label}</span></button>)}</div></div>;
}

function AppearanceForm({ settings, setSettings }: { settings: ArcenalAppearanceSettings; setSettings: (value: ArcenalAppearanceSettings) => void }): ReactElement {
  const patch = (values: Partial<ArcenalAppearanceSettings>): void => setSettings({ ...settings, ...values });
  return <div className="arc-appearance-form"><ColorField label="Couleur dominante" value={settings.accentColor} onChange={(accentColor) => patch({ accentColor })} /><ColorField label="Boutons" value={settings.buttonColor} onChange={(buttonColor) => patch({ buttonColor })} /><ColorField label="Liens" value={settings.linkColor} onChange={(linkColor) => patch({ linkColor })} /><ColorField label="Texte" value={settings.textColor} onChange={(textColor) => patch({ textColor })} /><UrlField label="Adresse du logo" value={settings.logoUrl} onChange={(logoUrl) => patch({ logoUrl })} /><UrlField label="Adresse du favicon" value={settings.faviconUrl} onChange={(faviconUrl) => patch({ faviconUrl })} /></div>;
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }): ReactElement {
  return <label className="arc-color-field"><span>{label}</span><input type="color" value={value} onChange={(event) => onChange(event.target.value)} /><code>{value}</code></label>;
}

function UrlField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }): ReactElement {
  const invalid = !isValidBrandUrl(value);
  return <label className="arc-field"><span>{label}</span><input aria-invalid={invalid} type="url" value={value} placeholder="https://…" onChange={(event) => onChange(event.target.value)} />{invalid && <small>Utilisez une adresse HTTP ou HTTPS.</small>}</label>;
}

function AppearancePreview({ settings }: { settings: ArcenalAppearanceSettings }): ReactElement {
  return <div className="arc-appearance-preview"><div className="arc-preview-brand">{settings.logoUrl ? <img src={settings.logoUrl} alt="Prévisualisation du logo" /> : <Image aria-hidden />}</div><div><small>Prévisualisation</small><strong>ARCenal Système</strong><a href="#appearance-preview" onClick={(event) => event.preventDefault()}>Lien d’exemple</a></div><button type="button">Action principale</button></div>;
}

async function saveAppearance(settings: ArcenalAppearanceSettings, setBusy: (value: boolean) => void, setStatus: (value: string) => void, reload: () => Promise<void>): Promise<void> {
  if (!isValidBrandUrl(settings.logoUrl) || !isValidBrandUrl(settings.faviconUrl)) return setStatus("Une adresse de personnalisation est invalide.");
  setBusy(true);
  setStatus("");
  try {
    await api.saveConfig(appearanceSettingsConfig(settings));
    await reload();
    window.dispatchEvent(new CustomEvent(ARCENAL_BRANDING_EVENT));
    setStatus("L’apparence d’ARC est enregistrée.");
  } catch (cause) {
    setStatus(cause instanceof Error ? cause.message : "Enregistrement impossible.");
  } finally {
    setBusy(false);
  }
}
