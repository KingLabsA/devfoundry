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
export const dockerRunning = () => invoke<boolean>("docker_running");
export const startDockerDesktop = () => invoke<void>("start_docker_desktop");

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Full startup flow: ensure the Docker daemon is up (launching Docker Desktop
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
