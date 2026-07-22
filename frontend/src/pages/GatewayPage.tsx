import { useCallback, useEffect, useState } from "react";
import { BASE } from "../api/client";
import { IS_TAURI, openUrlWindow } from "../api/native";

type GatewayInfo = {
  up: boolean;
  url: string;
  mode: string;
  native_installed: boolean;
  installable: boolean;
  docker_cli: boolean;
  docker_daemon: boolean;
  container: string | null;
  container_state: string | null;
  compose_dir: string | null;
  startable: boolean;
};

/** FreeLLMAPI dashboard + managed lifecycle. The gateway is a Docker service the
 *  app supervises: it auto-starts with the backend when Docker is running, and the
 *  Start button here handles the full path (launch Docker → start container).
 *  The dashboard sets X-Frame-Options: SAMEORIGIN so it can't be iframed — we
 *  open it in a native child window instead. */
export function GatewayPage() {
  const [info, setInfo] = useState<GatewayInfo | null>(null);
  const [starting, setStarting] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  const check = useCallback(async () => {
    try {
      const resp = await fetch(`${BASE}/api/embedded/freellmapi/status`);
      setInfo(await resp.json());
    } catch {
      setInfo(null);
    }
  }, []);

  useEffect(() => {
    check();
    const id = setInterval(check, 8000);
    return () => clearInterval(id);
  }, [check]);

  const startGateway = async () => {
    setStarting(true);
    setActionMsg(info?.native_installed ? "starting the embedded gateway (native)…"
      : info?.docker_daemon ? "starting the gateway container…"
      : "launching Docker, then the gateway container — this can take a minute…");
    try {
      const resp = await fetch(`${BASE}/api/embedded/freellmapi/start`, { method: "POST" });
      if (resp.ok) {
        setActionMsg("");
      } else {
        const body = await resp.json().catch(() => ({}));
        setActionMsg(`✗ ${body.detail || "start failed"}`);
      }
    } catch (err) {
      setActionMsg(`✗ ${String(err)}`);
    }
    await check();
    setStarting(false);
  };

  const embedGateway = async () => {
    setStarting(true);
    setActionMsg("embedding the gateway — clone + npm install + build, a few minutes one time…");
    try {
      const resp = await fetch(`${BASE}/api/embedded/freellmapi/install`, { method: "POST" });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setActionMsg(`✗ ${body.detail || "install failed"}`);
        setStarting(false);
        return;
      }
      setActionMsg("installed — starting…");
      await fetch(`${BASE}/api/embedded/freellmapi/start`, { method: "POST" });
      setActionMsg("");
    } catch (err) {
      setActionMsg(`✗ ${String(err)}`);
    }
    await check();
    setStarting(false);
  };

  const gatewayUrl = info?.url || "http://localhost:3002";
  const openWindow = () => openUrlWindow(gatewayUrl, "freellmapi-dashboard", "FreeLLMAPI Dashboard");

  const offlineDetail = () => {
    if (!info) return "backend unreachable";
    if (info.native_installed) return "the embedded gateway is stopped — Start runs it natively (no Docker).";
    if (info.installable) return "not embedded yet — Embed builds it into the app (no Docker needed).";
    if (!info.docker_cli) return "needs Node.js ≥ 20 (to embed) or Docker (legacy fallback).";
    if (!info.docker_daemon) return "Docker isn't running — Start launches Docker, then the gateway.";
    if (info.container) return `container ${info.container} is ${info.container_state || "stopped"}.`;
    if (info.compose_dir) return `will start the compose project in ${info.compose_dir}.`;
    return "no FreeLLMAPI install found — click Embed, or set FREELLMAPI_DIR.";
  };

  const modeLabel = info?.mode === "native" ? "embedded native" : info?.mode || "";

  return (
    <div className="page">
      <div className="page-head">
        <h2>Gateway — FreeLLMAPI</h2>
        <div className="page-actions"><button className="btn" onClick={check}>↻ Check</button></div>
      </div>

      <div className={`gateway-status ${info?.up ? "up" : "down"}`}>
        <span className={`dot ${info?.up ? "up" : "down"}`} />
        {info === null ? "checking…"
          : info.up ? <>Gateway is <strong>online</strong> at <code>{gatewayUrl}</code> ({modeLabel})</>
          : <>Gateway is <strong>offline</strong> — {offlineDetail()}</>}
        {info !== null && !info.up && info.startable && (
          <button className="btn primary" onClick={startGateway} disabled={starting} style={{ marginLeft: "auto" }}>
            {starting ? "⏳ starting…" : "▶ Start gateway"}
          </button>
        )}
        {info !== null && !info.up && !info.native_installed && info.installable && (
          <button className="btn" onClick={embedGateway} disabled={starting}
            style={{ marginLeft: info.startable ? undefined : "auto" }}>
            {starting ? "⏳ working…" : "⬇ Embed gateway"}
          </button>
        )}
      </div>
      {actionMsg && <p className="hint">{actionMsg}</p>}

      <div className="gateway-card">
        <p className="hint">
          The gateway is embedded: DevFoundry builds it once into the workspace and runs it as a
          supervised native process — auto-starting with the app, no Docker required (a legacy
          Docker container still works as a fallback).
          The FreeLLMAPI dashboard blocks embedding in iframes for security (<code>X-Frame-Options:
          SAMEORIGIN</code>), so it opens in its own window. That's where you add provider keys,
          browse the 60+ model catalog, and view usage.
        </p>
        <div className="gateway-actions">
          {IS_TAURI && (
            <button className="btn primary" onClick={openWindow} disabled={!info?.up}>
              🖥 Open dashboard in app window
            </button>
          )}
          <a className="btn" href={gatewayUrl} target="_blank" rel="noreferrer">Open in browser ↗</a>
        </div>
      </div>
    </div>
  );
}
