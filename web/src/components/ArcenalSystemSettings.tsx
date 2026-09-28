import { AlertTriangle, Archive, Boxes, Globe2, HardDrive, RefreshCw, RotateCcw, Server, ShieldCheck, Users } from "lucide-react";
import { useCallback, useEffect, useState, type ReactElement } from "react";
import { api, type ArcenalSystemCollection, type ArcenalSystemInventory, type ArcenalSystemOverview } from "@/lib/api";
import { isArcenalSystemInventory, systemRecordDetail, systemRecordLabel } from "@/lib/arcenal-system";
import { backupArchiveNames } from "@/lib/arcenal-backups";

interface SystemState {
  busy: boolean;
  error: string;
  inventory: ArcenalSystemInventory | null;
  overview: ArcenalSystemOverview | null;
}

const INITIAL: SystemState = { busy: true, error: "", inventory: null, overview: null };

export function ArcenalSystemSettingsPanel(): ReactElement {
  const { state, reload } = useSystemState();
  return (
    <section className="arc-settings-section">
      <PanelHeader busy={state.busy} title="État d’ARCenal Système" description="Données lues directement sur YunoHost et utilisées par les diagnostics d’ARC." onReload={reload} />
      {state.error && <p className="arc-alert arc-alert-error">{state.error}</p>}
      {state.overview && <ResourceGrid overview={state.overview} />}
      {state.inventory && <InventoryGrid inventory={state.inventory} />}
    </section>
  );
}

export function ArcenalBackupSettingsPanel(): ReactElement {
  const { state, reload } = useSystemState();
  const [operation, setOperation] = useState<BackupOperation>({ busy: false, error: "", notice: "", selected: "" });
  const backups = state.inventory?.backups;
  const create = (): void => { void createBackup(setOperation, reload); };
  const restore = (): void => { void restoreBackup(operation.selected, setOperation, reload); };
  return (
    <section className="arc-settings-section">
      <PanelHeader busy={state.busy} title="Sauvegardes YunoHost d’ARC" description="Archives détectées et contrôle de la protection des données applicatives." onReload={reload} />
      {state.error && <p className="arc-alert arc-alert-error">{state.error}</p>}
      {operation.error && <p className="arc-alert arc-alert-error">{operation.error}</p>}
      {operation.notice && <p className="arc-alert arc-alert-success">{operation.notice}</p>}
      <BackupSummary overview={state.overview} backups={backups} />
      <BackupActions backups={backups} create={create} operation={operation} restore={restore} setOperation={setOperation} />
      {backups && <SystemCollection icon={<Archive />} title="Archives disponibles" collection={backups} />}
      <p className="arc-backup-note"><ShieldCheck aria-hidden /> Configuration, contexte, mémoires, directives, RAG/LDA, métadonnées d’accès et audit sont inclus. Les secrets restent protégés dans les données YunoHost.</p>
    </section>
  );
}

function BackupActions({ backups, create, operation, restore, setOperation }: BackupActionProps): ReactElement {
  const names = backupNames(backups);
  return <div className="arc-backup-actions"><button className="arc-primary-button" disabled={operation.busy} onClick={create} type="button"><Archive /> Créer une sauvegarde</button><label><span>Archive à restaurer</span><select disabled={operation.busy} onChange={(event) => setOperation((current) => ({ ...current, selected: event.target.value }))} value={operation.selected}><option value="">Choisir une archive</option>{names.map((name) => <option key={name}>{name}</option>)}</select></label><button className="arc-danger-button" disabled={operation.busy || !operation.selected} onClick={restore} type="button"><RotateCcw /> Restaurer</button></div>;
}

async function createBackup(setOperation: SetBackupOperation, reload: () => Promise<void>): Promise<void> {
  setOperation((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    await api.prepareArcenalAction("arcenal.backup.create", null);
    await api.executeArcenalAction("arcenal.backup.create", null);
    setOperation((current) => ({ ...current, busy: false, notice: "La sauvegarde ARCenal a été créée." }));
    await reload();
  } catch (cause) {
    setOperation((current) => ({ ...current, busy: false, error: message(cause) }));
  }
}

async function restoreBackup(name: string, setOperation: SetBackupOperation, reload: () => Promise<void>): Promise<void> {
  if (!name || !window.confirm(`Restaurer l’archive ${name} ? Les données ARC actuelles seront remplacées.`)) return;
  setOperation((current) => ({ ...current, busy: true, error: "", notice: "" }));
  try {
    const prepared = await api.prepareArcenalAction("arcenal.backup.restore", name, true);
    if (!prepared.approval_id) throw new Error("La confirmation de restauration est absente.");
    await api.executeArcenalAction("arcenal.backup.restore", name, prepared.approval_id);
    setOperation((current) => ({ ...current, busy: false, notice: "ARCenal a été restauré. La page peut se reconnecter." }));
    await reload();
  } catch (cause) {
    setOperation((current) => ({ ...current, busy: false, error: message(cause) }));
  }
}

function backupNames(backups?: ArcenalSystemCollection): string[] {
  if (!backups) return [];
  return backupArchiveNames(backups.items);
}

function useSystemState(): { state: SystemState; reload: () => Promise<void> } {
  const [state, setState] = useState<SystemState>(INITIAL);
  const reload = useCallback(async (): Promise<void> => {
    setState((current) => ({ ...current, busy: true, error: "" }));
    try {
      const [overview, rawInventory] = await Promise.all([api.getArcenalSystemOverview(), api.getArcenalSystemInventory()]);
      if (!isArcenalSystemInventory(rawInventory)) throw new Error("L’inventaire YunoHost est incomplet.");
      setState({ busy: false, error: "", inventory: rawInventory, overview });
    } catch (cause) {
      setState((current) => ({ ...current, busy: false, error: message(cause) }));
    }
  }, []);
  useEffect(() => { void Promise.resolve().then(reload); }, [reload]);
  return { state, reload };
}

function PanelHeader({ busy, title, description, onReload }: { busy: boolean; title: string; description: string; onReload: () => Promise<void> }): ReactElement {
  return <div className="arc-settings-section-title arc-system-title"><span><Server /></span><div><small>Système</small><h2>{title}</h2><p>{description}</p></div><button className="arc-secondary-button" disabled={busy} type="button" onClick={() => void onReload()}><RefreshCw aria-hidden />Actualiser</button></div>;
}

function ResourceGrid({ overview }: { overview: ArcenalSystemOverview }): ReactElement {
  const resources = overview.resources;
  return <div className="arc-resource-grid"><Resource label="Santé" value={overview.health === "healthy" ? "Opérationnel" : "Dégradé"} /><Resource label="CPU" value={`${resources.cpu.load_percent} % · ${resources.cpu.cores} cœurs`} /><Resource label="Mémoire" value={`${resources.memory.percent} %`} /><Resource label="Stockage" value={`${resources.disk.percent} %`} /><Resource label="Charge" value={resources.load.join(" · ")} /></div>;
}

function Resource({ label, value }: { label: string; value: string }): ReactElement {
  return <article><span>{label}</span><strong>{value}</strong></article>;
}

function InventoryGrid({ inventory }: { inventory: ArcenalSystemInventory }): ReactElement {
  return <div className="arc-system-grid"><SystemCollection icon={<Boxes />} title="Applications" collection={inventory.applications} /><SystemCollection icon={<Globe2 />} title="Domaines" collection={inventory.domains} /><SystemCollection icon={<RefreshCw />} title="Mises à jour" collection={inventory.updates} /><SystemCollection icon={<ShieldCheck />} title="Certificats" collection={{ error: inventory.certificates.some((item) => item.error) ? "Certains certificats sont indisponibles." : "", items: inventory.certificates.map((item) => ({ domain: item.domain, status: item.error || certificateDetail(item.details) })) }} /><SystemCollection icon={<Users />} title="Utilisateurs" collection={inventory.users} /><SystemCollection icon={<AlertTriangle />} title="Diagnostics" collection={inventory.diagnostics} /><ErrorJournal errors={inventory.errors} /></div>;
}

function SystemCollection({ icon, title, collection }: { icon: ReactElement; title: string; collection: ArcenalSystemCollection }): ReactElement {
  return <article className="arc-system-card"><header>{icon}<strong>{title}</strong><small>{collection.items.length}</small></header>{collection.error && <p className="is-error">{collection.error}</p>}<ul>{collection.items.slice(0, 20).map((item, index) => <li key={`${systemRecordLabel(item)}-${index}`}><span>{systemRecordLabel(item)}</span><small>{systemRecordDetail(item)}</small></li>)}{!collection.error && collection.items.length === 0 && <li><span>Aucun élément signalé</span></li>}</ul></article>;
}

function ErrorJournal({ errors }: { errors: string[] }): ReactElement {
  const collection = { error: "", items: errors.map((line) => ({ label: line, status: "Erreur système" })) };
  return <SystemCollection icon={<HardDrive />} title="Erreurs récentes" collection={collection} />;
}

function BackupSummary({ overview, backups }: { overview: ArcenalSystemOverview | null; backups?: ArcenalSystemCollection }): ReactElement {
  return <div className="arc-backup-summary"><Archive aria-hidden /><div><small>Archives détectées</small><strong>{backups?.items.length ?? 0}</strong></div><div><small>État du serveur</small><strong>{overview?.health === "healthy" ? "Opérationnel" : "À vérifier"}</strong></div></div>;
}

function certificateDetail(details: unknown): string {
  if (typeof details !== "object" || details === null) return "État non communiqué";
  return JSON.stringify(details).slice(0, 140);
}

function message(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Lecture du système impossible.";
}

interface BackupOperation { busy: boolean; error: string; notice: string; selected: string }
type SetBackupOperation = React.Dispatch<React.SetStateAction<BackupOperation>>;
interface BackupActionProps { backups?: ArcenalSystemCollection; create: () => void; operation: BackupOperation; restore: () => void; setOperation: SetBackupOperation }
