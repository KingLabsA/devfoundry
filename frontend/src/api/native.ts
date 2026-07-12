import { invoke } from "@tauri-apps/api/core";

export const IS_TAURI = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

export const DEFAULT_PROJECT_DIR = "/Users/jahblesslion/Documents/devfoundry";

export function getProjectDir(): string {
  return localStorage.getItem("devfoundry.projectDir") || DEFAULT_PROJECT_DIR;
}

export function setProjectDir(dir: string) {
  localStorage.setItem("devfoundry.projectDir", dir);
}

export const dockerAvailable = () => invoke<boolean>("docker_available");
export const stackStatus = () => invoke<string>("stack_status", { dir: getProjectDir() });
export const startStack = () => invoke<string>("start_stack", { dir: getProjectDir() });
export const stopStack = () => invoke<string>("stop_stack", { dir: getProjectDir() });
export const serviceLogs = (service: string) => invoke<string>("service_logs", { dir: getProjectDir(), service });
export const readEnv = () => invoke<string>("read_env", { dir: getProjectDir() });
export const saveEnv = (content: string) => invoke<void>("save_env", { dir: getProjectDir(), content });

/** Parse .env text into ordered key/value pairs, preserving comments for round-trip. */
export function parseEnv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

/** Apply updated values onto the original .env text, keeping comments/order; append new keys. */
export function mergeEnv(original: string, updates: Record<string, string>): string {
  const seen = new Set<string>();
  const lines = original.split("\n").map((line) => {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=/);
    if (m && m[1] in updates) {
      seen.add(m[1]);
      return `${m[1]}=${updates[m[1]]}`;
    }
    return line;
  });
  const appended = Object.entries(updates)
    .filter(([k]) => !seen.has(k))
    .map(([k, v]) => `${k}=${v}`);
  return [...lines, ...appended].join("\n");
}
