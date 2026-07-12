const BASE = "http://localhost:9100";

export interface PipelineEvent {
  run_id: string;
  stage: string;
  kind: "log" | "artifact" | "status" | "error";
  message: string;
  payload: Record<string, unknown>;
  ts: string;
}

export async function createRun(idea: string): Promise<string> {
  const resp = await fetch(`${BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea }),
  });
  if (!resp.ok) throw new Error(`createRun failed: ${resp.status} ${await resp.text()}`);
  const data = await resp.json();
  return data.run_id;
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
