import { useCallback, useEffect, useState } from "react";

export type ArcColorMode = "light" | "dark" | "system";

const STORAGE_KEY = "arcenal-color-mode";
const CHANGE_EVENT = "arcenal-color-mode-change";

export function useArcColorMode(): { mode: ArcColorMode; setMode: (mode: ArcColorMode) => void } {
  const [mode, setCurrentMode] = useState<ArcColorMode>(readColorMode);
  useEffect(() => subscribeToMode(setCurrentMode), []);
  useEffect(() => applyColorMode(mode), [mode]);
  const setMode = useCallback((next: ArcColorMode): void => {
    window.localStorage.setItem(STORAGE_KEY, next);
    applyColorMode(next);
    window.dispatchEvent(new CustomEvent<ArcColorMode>(CHANGE_EVENT, { detail: next }));
  }, []);
  return { mode, setMode };
}

export function resolveColorMode(mode: ArcColorMode, systemDark: boolean): "light" | "dark" {
  if (mode === "system") return systemDark ? "dark" : "light";
  return mode;
}

function readColorMode(): ArcColorMode {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

function applyColorMode(mode: ArcColorMode): void {
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.arcColorMode = resolveColorMode(mode, systemDark);
}

function subscribeToMode(setMode: (mode: ArcColorMode) => void): () => void {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onMode = (event: Event): void => setMode((event as CustomEvent<ArcColorMode>).detail);
  const onSystem = (): void => applyColorMode(readColorMode());
  window.addEventListener(CHANGE_EVENT, onMode);
  media.addEventListener("change", onSystem);
  return () => { window.removeEventListener(CHANGE_EVENT, onMode); media.removeEventListener("change", onSystem); };
}
