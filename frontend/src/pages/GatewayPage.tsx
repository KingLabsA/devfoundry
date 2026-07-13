import { useEffect, useState } from "react";

const GATEWAY_URL = "http://localhost:3002";

/** Embeds the FreeLLMAPI dashboard (self-hosted gateway on :3002) inside the app. */
export function GatewayPage() {
  const [up, setUp] = useState<boolean | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        // no-cors: we only care that the server answers, not the body
        await fetch(GATEWAY_URL, { mode: "no-cors", signal: AbortSignal.timeout(3000) });
        if (alive) setUp(true);
      } catch {
        if (alive) setUp(false);
      }
    };
    check();
  }, [nonce]);

  return (
    <div className="page" style={{ gap: 10 }}>
      <div className="page-head">
        <h2>Gateway — FreeLLMAPI Dashboard</h2>
        <div className="page-actions">
          <a className="btn" href={GATEWAY_URL} target="_blank" rel="noreferrer">Open in browser ↗</a>
          <button className="btn" onClick={() => setNonce((n) => n + 1)}>↻ Reload</button>
        </div>
      </div>
      {up === false && (
        <div className="error">
          FreeLLMAPI gateway isn't responding at <code>{GATEWAY_URL}</code>. Start it (Docker: the
          <code> freellmapi</code> container), then Reload. The dashboard is where you add provider keys
          and see the model catalog.
        </div>
      )}
      <div className="gateway-frame">
        <iframe key={nonce} title="FreeLLMAPI" src={GATEWAY_URL}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
      </div>
    </div>
  );
}
