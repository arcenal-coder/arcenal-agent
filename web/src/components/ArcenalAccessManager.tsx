import { useEffect, useState, type Dispatch, type ReactElement, type SetStateAction } from "react";
import { Activity, CheckCircle2, KeyRound, Power, Trash2, UserRound } from "lucide-react";
import { api, type ArcenalAccessProbe } from "@/lib/api";
import { accessCredentialsFromConfig, createAccessCredential, isAccessStatusesResponse, type AccessCredential, type AccessCredentialDraft, type AccessCredentialKind } from "@/lib/arcenal-access";
import type { AutonomyLevel } from "@/lib/arcenal-providers";

interface AccessManagerProps {
  config: Record<string, unknown>;
  env: Record<string, { is_set?: boolean }>;
  reload: () => Promise<void>;
}

const EMPTY_DRAFT: AccessCredentialDraft = { autonomy: "manual", kind: "account", label: "", login: "", permissions: "lecture", secret: "", serviceUrl: "" };

export function ArcenalAccessManager({ config, env, reload }: AccessManagerProps): ReactElement {
  const [draft, setDraft] = useState<AccessCredentialDraft>(EMPTY_DRAFT);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [statuses, setStatuses] = useState<Record<string, ArcenalAccessProbe>>({});
  useEffect(() => { void loadStatuses(setStatuses, setMessage); }, []);
  const credentials = accessCredentialsFromConfig(config);
  const save = (): void => { void saveCredential(draft, credentials, setDraft, setMessage, setBusy, reload); };
  return <section className="arc-settings-section"><AccessHeading /><AccessForm busy={busy} draft={draft} save={save} setDraft={setDraft} />{message && <p className="arc-access-message" role="status">{message}</p>}<AccessList busy={busy} credentials={credentials} env={env} reload={reload} setBusy={setBusy} setMessage={setMessage} setStatuses={setStatuses} statuses={statuses} /></section>;
}

function AccessHeading(): ReactElement {
  return <div className="arc-settings-section-title"><span><KeyRound /></span><div><small>Coffre d’accès</small><h2>Comptes et API confiés à ARC</h2><p>Enregistrez les accès nécessaires à ses missions et limitez l’autonomie accordée pour chaque service.</p></div></div>;
}

function AccessForm({ busy, draft, save, setDraft }: { busy: boolean; draft: AccessCredentialDraft; save: () => void; setDraft: DraftSetter }): ReactElement {
  const patch = (values: Partial<AccessCredentialDraft>): void => setDraft((current) => ({ ...current, ...values }));
  return <div className="arc-access-form"><label><span>Type d’accès</span><select onChange={(event) => patch({ kind: event.target.value as AccessCredentialKind })} value={draft.kind}><option value="account">Login et mot de passe</option><option value="api">Clé API ou jeton</option></select></label><label><span>Nom du service</span><input onChange={(event) => patch({ label: event.target.value })} placeholder="Ex. Nextcloud production" value={draft.label} /></label><label><span>Adresse du service</span><input onChange={(event) => patch({ serviceUrl: event.target.value })} placeholder="https://service.example.com" type="url" value={draft.serviceUrl} /></label>{draft.kind === "account" && <label><span>Login</span><input autoComplete="off" onChange={(event) => patch({ login: event.target.value })} value={draft.login} /></label>}<label><span>{draft.kind === "api" ? "Clé API ou jeton" : "Mot de passe"}</span><input autoComplete="new-password" onChange={(event) => patch({ secret: event.target.value })} type="password" value={draft.secret} /></label><label><span>Permissions accordées</span><input onChange={(event) => patch({ permissions: event.target.value })} placeholder="lecture, fichiers, calendrier" value={draft.permissions} /></label><label><span>Autonomie sur ce service</span><select onChange={(event) => patch({ autonomy: event.target.value as AutonomyLevel })} value={draft.autonomy}><option value="manual">Lecture et conseil</option><option value="smart">Actions sûres</option><option value="off">Administration contrôlée</option></select></label><button className="arc-primary-button" disabled={busy} onClick={save} type="button">Confier cet accès à ARC</button></div>;
}

function AccessList({ busy, credentials, env, reload, setBusy, setMessage, setStatuses, statuses }: AccessListProps): ReactElement {
  if (credentials.length === 0) return <p className="arc-access-empty">Aucun accès métier n’est encore confié à ARC.</p>;
  return <div className="arc-access-list">{credentials.map((credential) => <AccessCard busy={busy} credential={credential} configured={env[credential.secretEnv]?.is_set === true} key={credential.id} reload={reload} setBusy={setBusy} setMessage={setMessage} setStatuses={setStatuses} status={statuses[credential.id]} allCredentials={credentials} />)}</div>;
}

function AccessCard({ allCredentials, busy, configured, credential, reload, setBusy, setMessage, setStatuses, status }: AccessCardProps): ReactElement {
  const remove = (): void => { void removeCredential(credential, allCredentials, setBusy, setMessage, reload); };
  const test = (): void => { void testCredential(credential, setBusy, setMessage, setStatuses); };
  const toggle = (): void => { void toggleCredential(credential, allCredentials, setBusy, setMessage, reload); };
  return <article className="arc-access-card" data-configured={configured} data-enabled={credential.enabled}><span>{credential.kind === "api" ? <KeyRound /> : <UserRound />}</span><div><strong>{credential.label}</strong><small>{credential.serviceUrl}</small><p>{credential.kind === "account" ? `Compte ${credential.login}` : "Authentification par API"} · {autonomyLabel(credential.autonomy)}</p><p>Permissions : {credential.permissions.join(", ") || "aucune permission déclarée"}</p>{status && <p className="arc-access-status" data-state={status.connection}>{status.message} · {formatDate(status.tested_at)}</p>}</div><em>{configured ? <><CheckCircle2 /> Secret enregistré</> : "Secret absent"}</em><div className="arc-access-actions"><button aria-label={`Tester ${credential.label}`} disabled={busy || !credential.enabled} onClick={test} type="button"><Activity /></button><button aria-label={`${credential.enabled ? "Désactiver" : "Activer"} ${credential.label}`} disabled={busy} onClick={toggle} type="button"><Power /></button><button aria-label={`Supprimer ${credential.label}`} disabled={busy} onClick={remove} type="button"><Trash2 /></button></div></article>;
}

async function saveCredential(draft: AccessCredentialDraft, credentials: AccessCredential[], setDraft: DraftSetter, setMessage: MessageSetter, setBusy: BusySetter, reload: () => Promise<void>): Promise<void> {
  setBusy(true);
  let credential: AccessCredential | null = null;
  let metadataSaved = false;
  try {
    credential = createAccessCredential(draft, credentials);
    await api.setArcenalSecret(credential.secretEnv, draft.secret.trim());
    await api.saveArcenalConfiguration({ arcenal: { access_credentials: [...credentials, credential] } });
    metadataSaved = true;
    setDraft(EMPTY_DRAFT);
    setMessage(`${credential.label} est maintenant disponible pour ARC.`);
    await reload();
  } catch (cause) {
    const cleanup = credential && !metadataSaved ? await cleanupSecret(credential.secretEnv) : "";
    setMessage(`${errorMessage(cause)}${cleanup}`);
  } finally {
    setBusy(false);
  }
}

async function cleanupSecret(secretEnv: string): Promise<string> {
  try {
    await api.deleteArcenalSecret(secretEnv);
    return "";
  } catch (cause) {
    return ` Le secret temporaire doit être supprimé manuellement : ${errorMessage(cause)}`;
  }
}

async function removeCredential(credential: AccessCredential, credentials: AccessCredential[], setBusy: BusySetter, setMessage: MessageSetter, reload: () => Promise<void>): Promise<void> {
  if (!window.confirm(`Retirer l’accès « ${credential.label} » ?`)) return;
  setBusy(true);
  try {
    await api.saveArcenalConfiguration({ arcenal: { access_credentials: credentials.filter((item) => item.id !== credential.id) } });
    await api.deleteArcenalSecret(credential.secretEnv);
    setMessage(`${credential.label} a été retiré du coffre d’ARC.`);
    await reload();
  } catch (cause) {
    setMessage(errorMessage(cause));
  } finally {
    setBusy(false);
  }
}

async function loadStatuses(setStatuses: StatusSetter, setMessage: MessageSetter): Promise<void> {
  try {
    const response = await api.getArcenalAccessStatuses();
    if (!isAccessStatusesResponse(response)) throw new Error("La réponse des accès ARC est incomplète.");
    setStatuses(response.accesses);
  } catch (cause) {
    setStatuses({});
    setMessage(`Les états précédents sont indisponibles : ${errorMessage(cause)}`);
  }
}

async function testCredential(credential: AccessCredential, setBusy: BusySetter, setMessage: MessageSetter, setStatuses: StatusSetter): Promise<void> {
  setBusy(true);
  try {
    const status = await api.testArcenalAccess(credential.id);
    if (!isAccessStatusesResponse({ accesses: { [credential.id]: status } })) throw new Error("La réponse de test de l’accès est incomplète.");
    setStatuses((current) => ({ ...current, [credential.id]: status }));
    setMessage(status.message);
  } catch (cause) {
    setMessage(errorMessage(cause));
  } finally {
    setBusy(false);
  }
}

async function toggleCredential(credential: AccessCredential, credentials: AccessCredential[], setBusy: BusySetter, setMessage: MessageSetter, reload: () => Promise<void>): Promise<void> {
  setBusy(true);
  try {
    const updated = credentials.map((item) => item.id === credential.id ? { ...item, enabled: !item.enabled } : item);
    await api.saveArcenalConfiguration({ arcenal: { access_credentials: updated } });
    setMessage(`${credential.label} est ${credential.enabled ? "désactivé" : "activé"}.`);
    await reload();
  } catch (cause) {
    setMessage(errorMessage(cause));
  } finally {
    setBusy(false);
  }
}

function autonomyLabel(level: AutonomyLevel): string {
  if (level === "off") return "administration contrôlée";
  if (level === "smart") return "actions sûres";
  return "lecture et conseil";
}

function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Cet accès n’a pas pu être enregistré.";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "date inconnue" : date.toLocaleString("fr-FR");
}

type DraftSetter = Dispatch<SetStateAction<AccessCredentialDraft>>;
type MessageSetter = Dispatch<SetStateAction<string>>;
type BusySetter = Dispatch<SetStateAction<boolean>>;
type StatusSetter = Dispatch<SetStateAction<Record<string, ArcenalAccessProbe>>>;
interface AccessListProps { busy: boolean; credentials: AccessCredential[]; env: Record<string, { is_set?: boolean }>; reload: () => Promise<void>; setBusy: BusySetter; setMessage: MessageSetter; setStatuses: StatusSetter; statuses: Record<string, ArcenalAccessProbe> }
interface AccessCardProps { allCredentials: AccessCredential[]; busy: boolean; configured: boolean; credential: AccessCredential; reload: () => Promise<void>; setBusy: BusySetter; setMessage: MessageSetter; setStatuses: StatusSetter; status?: ArcenalAccessProbe }
