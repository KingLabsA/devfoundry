import { useCallback, useEffect, useState } from "react";
import { HealthReport } from "../api/client";
import { IS_TAURI, dockerAvailable, ensureStackUp, serviceLogs, stackStatus, stopStack } from "../api/native";

interface ContainerRow {
  Service: string;
  State: string;
  Status: string;
}

const SERVICES = [
  { id: "backend", label: "Orchestrator API", port: 9100 },
  { id: "metagpt", label: "MetaGPT (specs)", port: 9101 },
  { id: "boltdiy", label: "Bolt.diy (codegen)", port: 9102 },
  { id: "opencode", label: "OpenCode (refine)", port: 9103 },
  { id: "orc", label: "Orc (tasks)", port: 9104 },
  { id: "superpowers", label: "Superpowers (deploy)", port: 9105 },
];

function parseStatus(raw: string): Record<string, ContainerRow> {
  const rows: Record<string, ContainerRow> = {};
  for (const line of raw.split("\n").filter(Boolean)) {
    try {
      const obj = JSON.parse(line);
      if (obj.Service) rows[obj.Service] = obj;
    } catch { /* non-JSON line */ }
  }
  return rows;
}

export function ServicesPage({ health }: { health: HealthReport | null }) {
  const [docker, setDocker] = useState<boolean | null>(null);
  const [containers, setContainers] = useState<Record<string, ContainerRow>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [logs, setLogs] = useState<{ service: string; text: string } | null>(null);

  const refresh = useCallback(async () => {
    if (!IS_TAURI) return;
    try {
      setDocker(await dockerAvailable());
      setContainers(parseStatus(await stackStatus()));
    } catch (err) {
      setMessage(String(err));
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 8000);
    return () => clearInterval(id);
  }, [refresh]);

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label);
    setMessage(`${label}…`);
    try {
      await fn();
      setMessage(`${label} — done`);
      await refresh();
    } catch (err) {
      setMessage(`${label} failed: ${err}`);
    } finally {
      setBusy(null);
    }
  };

  const showLogs = async (service: string) => {
    try {
      setLogs({ service, text: await serviceLogs(service) });
    } catch (err) {
      setLogs({ service, text: String(err) });
    }
  };

  if (!IS_TAURI) {
    return <div className="page"><div className="empty-state">Service management is available in the desktop app.</div></div>;
  }

  const embedded = health?.mode === "embedded" || health?.mode === "mock";
  const [qdrant, setQdrant] = useState<{ installed: boolean; running: boolean } | null>(null);
  const [qBusy, setQBusy] = useState(false);
  const [gw, setGw] = useState<{ up: boolean; mode: string; native_installed: boolean;
    installable: boolean; startable: boolean } | null>(null);
  const [gwBusy, setGwBusy] = useState(false);
  const [sandbox, setSandbox] = useState<{ enabled: boolean; backend: string | null } | null>(null);

  const refreshQdrant = useCallback(async () => {
    try {
      const r = await fetch("http://localhost:9100/api/embedded/qdrant/status");
      if (r.ok) setQdrant(await r.json());
    } catch { /* backend offline */ }
    try {
      const r = await fetch("http://localhost:9100/api/embedded/freellmapi/status");
      if (r.ok) setGw(await r.json());
    } catch { /* backend offline */ }
    try {
      const r = await fetch("http://localhost:9100/api/sandbox/status");
      if (r.ok) setSandbox(await r.json());
    } catch { /* backend offline */ }
  }, []);
  useEffect(() => { refreshQdrant(); const id = setInterval(refreshQdrant, 8000); return () => clearInterval(id); }, [refreshQdrant]);

  const qdrantAction = async (action: "install" | "start" | "stop") => {
    setQBusy(true);
    setMessage(action === "install" ? "Downloading Qdrant native binary (~40MB, one time)…" : `Qdrant: ${action}…`);
    try {
      const r = await fetch(`http://localhost:9100/api/embedded/qdrant/${action}`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || r.statusText);
      setMessage(`Qdrant ${action} — ok`);
      await refreshQdrant();
    } catch (err) {
      setMessage(`Qdrant ${action} failed: ${err}`);
    } finally {
      setQBusy(false);
    }
  };

  const gwAction = async (action: "install" | "start" | "stop") => {
    setGwBusy(true);
    setMessage(action === "install"
      ? "Embedding the gateway: clone + npm install + build — a few minutes, one time…"
      : `Gateway: ${action}…`);
    try {
      const r = await fetch(`http://localhost:9100/api/embedded/freellmapi/${action}`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || r.statusText);
      setMessage(`Gateway ${action} — ok`);
      await refreshQdrant();
    } catch (err) {
      setMessage(`Gateway ${action} failed: ${err}`);
    } finally {
      setGwBusy(false);
    }
  };

  return (
    <div className="page">
      <section className="settings-group">
        <h3>Embedded services — built in, no Docker</h3>
        <p className="hint">Native services managed by DevFoundry. <strong>Qdrant</strong> powers semantic RAG
          (falls back to local embeddings without it); the <strong>FreeLLMAPI gateway</strong> runs as a plain
          Node child process; the <strong>sandbox</strong> confines generated code using the OS itself.</p>
        <div className="field-row" style={{ alignItems: "center" }}>
          <span className={`dot ${qdrant?.running ? "up" : "down"}`} />
          <span style={{ fontSize: 13 }}>Qdrant vector store
            {qdrant ? (qdrant.running ? " — running (native)" : qdrant.installed ? " — installed, stopped" : " — not installed") : " — checking…"}
          </span>
          {qdrant && !qdrant.installed && (
            <button className="btn small primary" disabled={qBusy} onClick={() => qdrantAction("install")}>⬇ Install (native)</button>
          )}
          {qdrant?.installed && !qdrant.running && (
            <button className="btn small primary" disabled={qBusy} onClick={() => qdrantAction("start")}>▶ Start</button>
          )}
          {qdrant?.running && (
            <button className="btn small" disabled={qBusy} onClick={() => qdrantAction("stop")}>■ Stop</button>
          )}
        </div>
        <div className="field-row" style={{ alignItems: "center" }}>
          <span className={`dot ${gw?.up ? "up" : "down"}`} />
          <span style={{ fontSize: 13 }}>FreeLLMAPI gateway
            {gw ? (gw.up ? ` — running (${gw.mode})` : gw.native_installed ? " — embedded, stopped" : " — not embedded") : " — checking…"}
          </span>
          {gw && !gw.native_installed && gw.installable && (
            <button className="btn small primary" disabled={gwBusy} onClick={() => gwAction("install")}>⬇ Embed (native)</button>
          )}
          {gw && !gw.up && gw.startable && (
            <button className="btn small primary" disabled={gwBusy} onClick={() => gwAction("start")}>▶ Start</button>
          )}
          {gw?.up && (
            <button className="btn small" disabled={gwBusy} onClick={() => gwAction("stop")}>■ Stop</button>
          )}
        </div>
        <div className="field-row" style={{ alignItems: "center" }}>
          <span className={`dot ${sandbox?.enabled && sandbox.backend ? "up" : "down"}`} />
          <span style={{ fontSize: 13 }}>Code sandbox
            {sandbox ? (sandbox.enabled && sandbox.backend
              ? ` — active (${sandbox.backend}, OS-native): generated code writes confined to the project`
              : sandbox.enabled ? " — no backend on this OS (code runs unconfined)"
              : " — disabled via SANDBOX=0") : " — checking…"}
          </span>
        </div>
      </section>
      {embedded && (
        <div className="notice">
          <strong>Embedded mode</strong> — all pipeline stages run inside the app; nothing external is required.
          The Docker controls below are optional (“isolated mode”) for containerized engines and deploys.
        </div>
      )}
      <div className="page-head">
        <h2>{embedded ? "Isolated mode (optional)" : "Services"}</h2>
        <div className="page-actions">
          <button className="btn primary" disabled={busy !== null || docker === false}
            onClick={() => run("Starting stack", () => ensureStackUp(setMessage))}>
            {busy ? "Working…" : "▶ Start All"}
          </button>
          <button className="btn" disabled={busy !== null || docker === false}
            onClick={() => run("Stopping stack", stopStack)}>
            ■ Stop All
          </button>
          <button className="btn" onClick={refresh}>↻ Refresh</button>
        </div>
      </div>

      {docker === false && (
        <div className="error">
          Docker is not available. Install Docker Desktop (or start the Docker daemon) — DevFoundry manages the
          service stack for you once Docker is running.
        </div>
      )}
      {message && <div className="notice">{message}</div>}

      <table className="services-table">
        <thead>
          <tr><th>Service</th><th>Port</th><th>Container</th><th>Health</th><th /></tr>
        </thead>
        <tbody>
          {SERVICES.map((s) => {
            const c = containers[s.id];
            const healthy = s.id === "backend" ? health?.backend === "ok" : Boolean(health?.[s.id as keyof HealthReport]);
            return (
              <tr key={s.id}>
                <td>{s.label}</td>
                <td className="mono">:{s.port}</td>
                <td>
                  <span className={`badge ${c?.State === "running" ? "ok" : "off"}`}>
                    {c ? c.State : "not created"}
                  </span>
                </td>
                <td><span className={`dot ${healthy ? "up" : "down"}`} /></td>
                <td><button className="btn small" onClick={() => showLogs(s.id)}>logs</button></td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {logs && (
        <div className="logs-modal" onClick={() => setLogs(null)}>
          <div className="logs-box" onClick={(e) => e.stopPropagation()}>
            <div className="logs-head">
              <strong>{logs.service} — last 200 lines</strong>
              <button className="btn small" onClick={() => setLogs(null)}>close</button>
            </div>
            <pre>{logs.text || "(no output)"}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
