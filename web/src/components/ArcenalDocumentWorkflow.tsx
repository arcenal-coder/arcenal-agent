import { History, RotateCcw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type ReactElement } from "react";
import { api, type ArcenalDocumentHistoryVersion, type ArcenalDocumentStatus, type ArcenalDocumentSummary } from "@/lib/api";
import { nextDocumentStatuses } from "@/lib/arcenal-knowledge";

interface WorkflowProps {
  document: ArcenalDocumentSummary;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
}

export function ArcenalDocumentWorkflow({ document, onChanged, onError }: WorkflowProps): ReactElement {
  const [versions, setVersions] = useState<ArcenalDocumentHistoryVersion[]>([]);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async (): Promise<void> => {
    const result = await api.getArcenalDocumentHistory(document.path);
    setVersions(result.versions);
  }, [document.path]);
  useEffect(() => { void Promise.resolve().then(load).catch((cause: unknown) => onError(message(cause))); }, [load, onError]);
  const transition = async (status: ArcenalDocumentStatus): Promise<void> => run(async () => {
    if (!confirmTransition(status)) return;
    const reason = window.prompt("Motif de cette transition documentaire :", "") ?? "";
    await api.transitionArcenalDocument(document.path, status, reason);
    await onChanged();
  }, setBusy, onError);
  const restore = async (version: ArcenalDocumentHistoryVersion): Promise<void> => run(async () => {
    if (!window.confirm(`Restaurer la version ${version.version} (${version.status}) ?`)) return;
    await api.restoreArcenalDocumentHistory(document.path, version.id);
    await onChanged();
  }, setBusy, onError);
  return <WorkflowView busy={busy} document={document} versions={versions} onRestore={restore} onTransition={transition} />;
}

function WorkflowView({ busy, document, versions, onRestore, onTransition }: { busy: boolean; document: ArcenalDocumentSummary; versions: ArcenalDocumentHistoryVersion[]; onRestore: (version: ArcenalDocumentHistoryVersion) => Promise<void>; onTransition: (status: ArcenalDocumentStatus) => Promise<void> }): ReactElement {
  return (
    <section className="arc-document-workflow">
      <span><ShieldCheck aria-hidden /> Circuit documentaire</span>
      <div className="arc-workflow-actions">{nextDocumentStatuses(document.status).map((status) => <button disabled={busy} key={status} type="button" onClick={() => void onTransition(status)}>{actionLabel(status)}</button>)}</div>
      <header><History aria-hidden /><strong>Versions antérieures</strong><small>{versions.length}</small></header>
      {versions.length > 0 ? <ul>{versions.map((version) => <li key={version.id}><span><strong>v{version.version} · {version.status}</strong><small>{version.id}</small></span><button disabled={busy} type="button" onClick={() => void onRestore(version)}><RotateCcw aria-hidden />Restaurer</button></li>)}</ul> : <p>Aucune version antérieure.</p>}
    </section>
  );
}

async function run(action: () => Promise<void>, setBusy: (value: boolean) => void, onError: (message: string) => void): Promise<void> {
  setBusy(true);
  try { await action(); }
  catch (cause) { onError(message(cause)); }
  finally { setBusy(false); }
}

function confirmTransition(status: ArcenalDocumentStatus): boolean {
  if (status === "Applicable") return window.confirm("Approuver et publier cette version dans la LDA et le wiki ?");
  if (status === "Archivé") return window.confirm("Archiver cette version documentaire ?");
  return true;
}

function actionLabel(status: ArcenalDocumentStatus): string {
  if (status === "Applicable") return "Approuver et publier";
  if (status === "Archivé") return "Archiver";
  return `Passer à « ${status} »`;
}

function message(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Circuit documentaire indisponible.";
}
