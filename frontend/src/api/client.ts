export const BASE = "http://localhost:9100";

export interface DeployOptions {
  deploy_target?: string;
  custom_domain?: string;
}

export interface ProjectFile {
  path: string;
  size: number;
}

export interface PipelineEvent {
  run_id: string;
  stage: string;
  kind: "log" | "artifact" | "status" | "error";
  message: string;
  payload: Record<string, unknown>;
  ts: string;
}

export interface HealthReport {
  backend: string;
  mode?: "embedded" | "isolated" | "mock";
  metagpt: boolean;
  boltdiy: boolean;
  opencode: boolean;
  orc: boolean;
  superpowers: boolean;
}

export async function createRun(idea: string, opts: DeployOptions = {}): Promise<string> {
  const resp = await fetch(`${BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea, ...opts }),
  });
  if (!resp.ok) throw new Error(`createRun failed: ${resp.status} ${await resp.text()}`);
  const data = await resp.json();
  return data.run_id;
}

export async function stopRun(runId: string): Promise<boolean> {
  const resp = await fetch(`${BASE}/api/runs/${runId}/stop`, { method: "POST" });
  if (!resp.ok) return false;
  return (await resp.json()).stopped;
}

export async function redeploy(runId: string, opts: DeployOptions): Promise<Record<string, unknown>> {
  const resp = await fetch(`${BASE}/api/runs/${runId}/redeploy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  });
  if (!resp.ok) throw new Error(`redeploy failed: ${await resp.text()}`);
  return await resp.json();
}

export async function listProjectFiles(runId: string): Promise<ProjectFile[]> {
  const resp = await fetch(`${BASE}/api/runs/${runId}/files`);
  if (!resp.ok) return [];
  return await resp.json();
}

export async function readProjectFile(runId: string, path: string): Promise<{ content: string; binary: boolean }> {
  const resp = await fetch(`${BASE}/api/runs/${runId}/file?path=${encodeURIComponent(path)}`);
  if (!resp.ok) throw new Error(await resp.text());
  return await resp.json();
}

export async function writeProjectFile(runId: string, path: string, content: string): Promise<void> {
  const resp = await fetch(`${BASE}/api/runs/${runId}/file`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!resp.ok) throw new Error(await resp.text());
}

export function downloadUrl(runId: string): string {
  return `${BASE}/api/runs/${runId}/download`;
}

export async function uploadProjectZip(runId: string, file: File): Promise<number> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${BASE}/api/runs/${runId}/upload`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(await resp.text());
  return (await resp.json()).uploaded;
}

export async function fetchHealth(): Promise<HealthReport | null> {
  try {
    const resp = await fetch(`${BASE}/api/health`);
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

export function openRunStream(runId: string, onEvent: (e: PipelineEvent) => void, onClose: () => void): WebSocket {
  const ws = new WebSocket(`${BASE.replace("http", "ws")}/ws/runs/${runId}`);
  ws.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data));
    } catch (err) {
      console.error("bad event payload", err);
    }
  };
  ws.onerror = (err) => console.error("ws error", err);
  ws.onclose = onClose;
  return ws;
}
