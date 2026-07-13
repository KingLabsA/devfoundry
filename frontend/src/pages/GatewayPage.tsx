import { useCallback, useEffect, useState } from "react";
import { BASE } from "../api/client";
import { IS_TAURI, openUrlWindow } from "../api/native";

const GATEWAY_URL = "http://localhost:3002";

/** FreeLLMAPI dashboard. The dashboard sets X-Frame-Options: SAMEORIGIN so it
 *  can't be iframed — we open it in a native child window instead. */
export function GatewayPage() {
  const [status, setStatus] = useState<{ up: boolean; status: number } | null>(null);

  const check = useCallback(async () => {
    try {
      const resp = await fetch(`${BASE}/api/gateway/status`);
      setStatus(await resp.json());
    } catch {
      setStatus({ up: false, status: 0 });
    }
  }, []);

  useEffect(() => {
    check();
    const id = setInterval(check, 8000);
    return () => clearInterval(id);
  }, [check]);

  const openWindow = () => openUrlWindow(GATEWAY_URL, "freellmapi-dashboard", "FreeLLMAPI Dashboard");

  return (
    <div className="page">
      <div className="page-head">
        <h2>Gateway — FreeLLMAPI</h2>
        <div className="page-actions"><button className="btn" onClick={check}>↻ Check</button></div>
      </div>

      <div className={`gateway-status ${status?.up ? "up" : "down"}`}>
        <span className={`dot ${status?.up ? "up" : "down"}`} />
        {status === null ? "checking…"
          : status.up ? <>Gateway is <strong>online</strong> at <code>{GATEWAY_URL}</code> (HTTP {status.status})</>
          : <>Gateway is <strong>offline</strong> — start the <code>freellmapi</code> Docker container.</>}
      </div>

      <div className="gateway-card">
        <p className="hint">
          The FreeLLMAPI dashboard blocks embedding for security (<code>X-Frame-Options: SAMEORIGIN</code>),
          so it opens in its own window. That's where you add provider keys, browse the 60+ model catalog,
          and view usage.
        </p>
        <div className="gateway-actions">
          {IS_TAURI && (
            <button className="btn primary" onClick={openWindow} disabled={!status?.up}>
              🖥 Open dashboard in app window
            </button>
          )}
          <a className="btn" href={GATEWAY_URL} target="_blank" rel="noreferrer">Open in browser ↗</a>
        </div>
      </div>
    </div>
  );
}
