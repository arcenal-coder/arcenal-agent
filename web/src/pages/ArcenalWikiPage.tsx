import { useCallback, useEffect, useMemo, useState, type ReactElement } from "react";
import { BookOpen, FileCheck2, Search } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { ARCENAL_LOGO_PATH } from "@/brand";
import { api, HERMES_BASE_PATH, type ArcenalDocumentSummary } from "@/lib/api";
import { filterDocuments } from "@/lib/arcenal-knowledge";

export default function ArcenalWikiPage(): ReactElement {
  const [documents, setDocuments] = useState<ArcenalDocumentSummary[]>([]);
  const [selectedPath, setSelectedPath] = useState("");
  const [content, setContent] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async (): Promise<void> => {
    try {
      const overview = await api.getArcenalWiki();
      setDocuments(overview.wiki);
      setSelectedPath((current) => current || overview.wiki[0]?.path || "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Le wiki est momentanément indisponible.");
    }
  }, []);
  const activePath = documents.some((document) => document.path === selectedPath)
    ? selectedPath
    : documents[0]?.path ?? "";

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!activePath) return;
    let cancelled = false;
    void api.getArcenalWikiDocument(activePath)
      .then((result) => {
        if (!cancelled) setContent(result.content);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "Lecture impossible.");
    });
    return () => { cancelled = true; };
  }, [activePath]);

  const visible = useMemo(() => filterDocuments(documents, query), [documents, query]);
  const selected = documents.find((document) => document.path === activePath) ?? null;
  return <div className="arc-wiki-public"><header><img src={`${HERMES_BASE_PATH}${ARCENAL_LOGO_PATH}`} alt="ARCenal" /><span><strong>Wiki QSSERP</strong><small>Référentiel documentaire applicable</small></span><em>Lecture contrôlée</em></header><main><aside><div className="arc-search"><Search aria-hidden /><input aria-label="Rechercher dans le wiki" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher une procédure…" /></div><p><BookOpen aria-hidden /> Documents applicables <b>{visible.length}</b></p><nav>{visible.map((document) => <button type="button" key={document.path} className={document.path === activePath ? "is-selected" : ""} onClick={() => setSelectedPath(document.path)}><FileCheck2 aria-hidden /><span><strong>{document.title}</strong><small>{document.reference} · version {document.version}</small></span></button>)}</nav></aside><article>{error && <p className="arc-alert arc-alert-error">{error}</p>}{selected ? <><header><span>{selected.type} · {selected.reference}</span><h1>{selected.title}</h1><p>Version {selected.version} · Applicable{selected.application_date ? ` depuis le ${selected.application_date}` : ""}</p></header><div className="arc-wiki-content"><Markdown content={withoutFrontmatter(content)} /></div></> : <div className="arc-empty-canvas"><BookOpen aria-hidden /><h1>Bienvenue dans le wiki QSSERP</h1><p>Aucun document n’est actuellement publié. Les brouillons et révisions restent invisibles jusqu’à leur approbation.</p></div>}</article></main><footer>Publié par ARCenal Agent · sources issues de la LDA contrôlée</footer></div>;
}

function withoutFrontmatter(content: string): string {
  return content.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, "");
}
