import type * as React from "react";

interface ArcenalPluginGateway {
  createClient(): unknown;
}

interface ArcenalPluginSdk {
  React: typeof React;
  fetchJSON<Result>(url: string, init?: RequestInit): Promise<Result>;
  gateway: ArcenalPluginGateway;
}

interface ArcenalPluginRegistry {
  register(name: string, component: React.ComponentType<Record<string, never>>): void;
}

declare global {
  interface Window {
    __HERMES_PLUGINS__?: ArcenalPluginRegistry;
    __HERMES_PLUGIN_SDK__?: ArcenalPluginSdk;
  }
}

export {};
