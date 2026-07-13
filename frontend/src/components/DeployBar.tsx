import { useEffect, useState } from "react";
import { BASE, redeploy } from "../api/client";

interface Provider { id: string; label: string; configured: boolean }

const DOMAIN_TARGETS = new Set(["netlify", "surge"]);

export function DeployBar({
  target, domain, onTarget, onDomain, runId, onRedeployed,
}: {
  target: string;
  domain: string;
  onTarget: (t: string) => void;
  onDomain: (d: string) => void;
  runId?: string | null;
  onRedeployed?: (result: Record<string, unknown>) => void;
}) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch(`${BASE}/api/deploy/providers`).then((r) => r.json()).then(setProviders).catch(() => {});
  }, []);

  const doRedeploy = async () => {
    if (!runId) return;
    setBusy(true);
    setStatus("Re-deploying…");
    try {
      const result = await redeploy(runId, { deploy_target: target, custom_domain: domain });
      setStatus(`Deployed: ${result.url || result.image || result.bundle}`);
      onRedeployed?.(result);
    } catch (err) {
      setStatus(`${err}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="deploy-bar">
      <span className="deploy-label">🚀 Deploy to</span>
      <select className="btn" value={target} onChange={(e) => onTarget(e.target.value)}>
        {providers.map((p) => (
          <option key={p.id} value={p.id}>{p.label}{p.configured ? "" : " (needs token)"}</option>
        ))}
      </select>
      {DOMAIN_TARGETS.has(target) && (
        <input className="deploy-domain" placeholder="custom domain (e.g. myapp.surge.sh)"
          value={domain} onChange={(e) => onDomain(e.target.value)} spellCheck={false} />
      )}
      {runId && (
        <button className="btn small primary" onClick={doRedeploy} disabled={busy}>
          {busy ? "…" : "Re-deploy"}
        </button>
      )}
      {status && <span className="deploy-status">{status}</span>}
    </div>
  );
}
