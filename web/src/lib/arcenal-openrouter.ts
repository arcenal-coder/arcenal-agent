import type { ArcenalOpenRouterProbeResponse, ModelOptionsResponse } from "@/lib/api";

export interface OpenRouterModelSelection {
  current: string;
  models: string[];
}

export function openRouterModelSelection(options: ModelOptionsResponse): OpenRouterModelSelection {
  const provider = options.providers?.find((item) => item.slug.toLowerCase() === "openrouter");
  const models = [...new Set(provider?.models ?? [])].filter((model) => model.trim().length > 0);
  const current = (options.provider ?? "").toLowerCase() === "openrouter" ? options.model ?? "" : "";
  return { current: models.includes(current) ? current : models[0] ?? "", models };
}

export function connectionLabel(status: ArcenalOpenRouterProbeResponse | null): string {
  if (!status) return "État non vérifié";
  if (status.connection === "connected") return "Connecté";
  if (status.connection === "invalid") return "Clé refusée";
  if (status.connection === "unreachable") return "Service indisponible";
  return "Non configuré";
}
