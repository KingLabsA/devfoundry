import { invoke } from "@tauri-apps/api/core";

export const IS_TAURI = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

export const DEFAULT_PROJECT_DIR = "/Users/jahblesslion/Documents/devfoundry";

export function getProjectDir(): string {
  return localStorage.getItem("devfoundry.projectDir") || DEFAULT_PROJECT_DIR;
}

export function setProjectDir(dir: string) {
  localStorage.setItem("devfoundry.projectDir", dir);
}

export const openUrlWindow = (url: string, label: string, title: string) =>
  invoke<void>("open_url_window", { url, label, title });

export const startDevServer = (project_dir: string) => invoke<number>("start_dev_server", { projectDir: project_dir });
export const stopDevServer = (project_dir: string) => invoke<void>("stop_dev_server", { projectDir: project_dir });

export const keychainSet = (key: string, value: string) => invoke<void>("keychain_set", { key, value });
export const keychainGet = (key: string) => invoke<string>("keychain_get", { key });
export const keychainDelete = (key: string) => invoke<void>("keychain_delete", { key });

export interface Specs { ram_gb: number; cpu_cores: number; arch: string; chip: string; gpu: string }
export const systemSpecs = () => invoke<Record<string, string>>("system_specs").then((s) => ({
  ram_gb: Number(s.ram_gb || 0), cpu_cores: Number(s.cpu_cores || 0),
  arch: s.arch || "", chip: s.chip || "", gpu: s.gpu || "",
} as Specs));

export const dockerAvailable = () => invoke<boolean>("docker_available");
export const dockerRunning = () => invoke<boolean>("docker_running");
export const startDockerDesktop = () => invoke<void>("start_docker_desktop");

export const startBackend = () => invoke<string>("start_backend", { dir: getProjectDir() });
export const stopBackend = () => invoke<void>("stop_backend");

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function backendHealthy(): Promise<boolean> {
  try {
    const resp = await fetch("http://localhost:9100/api/health", { signal: AbortSignal.timeout(3000) });
    return resp.ok;
  } catch {
    return false;
  }
}

/**
 * Default startup: the embedded orchestrator runs everything in-process —
 * no Docker required. Spawns it via the native command and waits for health.
 */
export async function ensureEmbeddedUp(onProgress: (msg: string) => void): Promise<void> {
  if (await backendHealthy()) {
    onProgress("Services already running.");
    return;
  }
  onProgress("Starting embedded orchestrator…");
  await startBackend();
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    await sleep(1500);
    if (await backendHealthy()) {
      onProgress("Services running (embedded mode).");
      return;
    }
  }
  throw new Error(
    "Embedded orchestrator did not come up. Check that Python 3.11+ is installed " +
    "(or backend/.venv exists), or switch to Docker isolated mode from the Services page.",
  );
}

/**
 * Isolated mode: ensure the Docker daemon is up (launching Docker Desktop
 * if needed), then bring the compose stack up. Reports progress via callback.
 */
export async function ensureStackUp(onProgress: (msg: string) => void): Promise<void> {
  if (!(await dockerAvailable())) {
    throw new Error("Docker is not installed. Install Docker Desktop from docker.com, then try again.");
  }
  if (!(await dockerRunning())) {
    onProgress("Docker daemon is not running — launching Docker Desktop…");
    await startDockerDesktop();
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      await sleep(3000);
      if (await dockerRunning()) break;
      onProgress("Waiting for Docker daemon to start…");
    }
    if (!(await dockerRunning())) {
      throw new Error("Docker Desktop did not become ready within 2 minutes. Open it manually, then retry.");
    }
  }
  onProgress("Docker is up — starting DevFoundry services (first run builds images, this can take several minutes)…");
  await startStack();
  onProgress("Services started.");
}
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
