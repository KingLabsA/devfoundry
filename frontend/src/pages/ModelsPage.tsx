import { useCallback, useEffect, useState } from "react";
import { IS_TAURI, mergeEnv, readEnv, saveEnv } from "../api/native";

const BASE = "http://localhost:9100";

interface Provider {
  id: string;
  label: string;
  kind: string;
  free: boolean;
  local: boolean;
  base_url: string;
  key_env: string;
  default_model: string;
  configured: boolean;
  active: boolean;
}

interface Routing {
  active_provider: string;
  active_model: string;
  rotation: string[];
  stage_experts: Record<string, string>;
  autodetected_local: { provider: string; model: string } | null;
}

export function ModelsPage() {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [routing, setRouting] = useState<Routing | null>(null);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [models, setModels] = useState<{ provider: Provider; list: string[] } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [rotationInput, setRotationInput] = useState("");
  const [experts, setExperts] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    try {
      const [p, r] = await Promise.all([
        fetch(`${BASE}/api/llm/providers`).then((x) => x.json()),
        fetch(`${BASE}/api/llm/routing`).then((x) => x.json()),
      ]);
      setProviders(p);
      setRouting(r);
      setRotationInput(r.rotation.join(", "));
      setExperts(r.stage_experts);
    } catch {
      setProviders(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const saveToEnv = async (updates: Record<string, string>) => {
    const original = await readEnv();
    await saveEnv(mergeEnv(original, updates));
  };

  const saveKey = async (p: Provider) => {
    const key = keyInputs[p.id];
    if (!key || !p.key_env) return;
    setBusy(p.id);
    try {
      await saveToEnv({ [p.key_env]: key });
      setKeyInputs((k) => ({ ...k, [p.id]: "" }));
      setMessage(`${p.label}: key saved — takes effect immediately`);
      await refresh();
    } catch (err) {
      setMessage(`Save failed: ${err}`);
    } finally {
      setBusy(null);
    }
  };

  const fetchModels = async (p: Provider) => {
    setBusy(p.id);
    setMessage(`${p.label}: fetching models…`);
    try {
      const resp = await fetch(`${BASE}/api/llm/providers/${p.id}/models`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || resp.statusText);
      setModels({ provider: p, list: data.models });
      setMessage(`${p.label}: ${data.count} models available`);
    } catch (err) {
      setMessage(`${p.label}: ${err}`);
    } finally {
      setBusy(null);
    }
  };

  const selectModel = async (p: Provider, model: string) => {
    setBusy(p.id);
    try {
      await saveToEnv({ LLM_PROVIDER: p.id, LLM_MODEL: model });
      setModels(null);
      setMessage(`Active: ${p.label} → ${model}`);
      await refresh();
    } catch (err) {
      setMessage(`Select failed: ${err}`);
    } finally {
      setBusy(null);
    }
  };

  const testLLM = async () => {
    setBusy("__test");
    setMessage("Testing LLM (rotation + auto-detect active)…");
    try {
      const resp = await fetch(`${BASE}/api/llm/test`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || resp.statusText);
      setMessage(`✓ LLM working — response: "${data.response}"`);
    } catch (err) {
      setMessage(`LLM test failed: ${err}`);
    } finally {
      setBusy(null);
    }
  };

  const saveRouting = async () => {
    setBusy("__routing");
    try {
      await saveToEnv({
        LLM_ROTATION: rotationInput,
        LLM_MODEL_SPEC: experts.spec ?? "",
        LLM_MODEL_CODEGEN: experts.codegen ?? "",
        LLM_MODEL_TASKS: experts.tasks ?? "",
        LLM_MODEL_REFINE: experts.refine ?? "",
      });
      setMessage("Routing saved — applies immediately");
      await refresh();
    } catch (err) {
      setMessage(`Save failed: ${err}`);
    } finally {
      setBusy(null);
    }
  };

  if (providers === null) {
    return <div className="page"><div className="empty-state">Backend offline — models load once services are running.</div></div>;
  }

  const active = providers.find((p) => p.active);

  return (
    <div className="page">
      <div className="page-head">
        <h2>Models — {providers.length} providers</h2>
        <div className="page-actions">
          <button className="btn primary" onClick={testLLM} disabled={busy !== null}>⚡ Test LLM</button>
          <button className="btn" onClick={refresh}>↻ Refresh</button>
        </div>
      </div>
      {active ? (
        <div className="notice">Active: <strong>{active.label}</strong>{routing?.active_model ? ` → ${routing.active_model}` : ""} — click “models” on any provider to switch.</div>
      ) : routing?.autodetected_local ? (
        <div className="notice">No provider selected — auto-detected local runtime: <strong>{routing.autodetected_local.provider} → {routing.autodetected_local.model}</strong> will be used. Pick a model below to choose explicitly.</div>
      ) : null}
      {message && <div className="notice">{message}</div>}

      {IS_TAURI && (
        <section className="settings-group">
          <h3>Routing — rotation & MoE stage experts</h3>
          <p className="hint">
            <strong>Rotation:</strong> comma-separated fallbacks tried in order on rate-limits/errors, e.g.
            <code>groq:llama-3.3-70b-versatile, openrouter:openrouter/auto, ollama:qwen2.5</code>.{" "}
            <strong>Stage experts (MoE):</strong> a different model per pipeline stage; format <code>provider:model</code> or bare model (uses active provider). Blank = active model.
          </p>
          <label className="field">
            <span>Rotation list</span>
            <input value={rotationInput} onChange={(e) => setRotationInput(e.target.value)}
              placeholder="groq:llama-3.3-70b-versatile, ollama:qwen2.5" spellCheck={false} />
          </label>
          <div className="field-row">
            {(["spec", "codegen", "tasks", "refine"] as const).map((r) => (
              <label className="field" style={{ flex: 1 }} key={r}>
                <span>{r} expert</span>
                <input value={experts[r] ?? ""} placeholder="provider:model"
                  onChange={(e) => setExperts((x) => ({ ...x, [r]: e.target.value }))} spellCheck={false} />
              </label>
            ))}
          </div>
          <button className="btn primary" style={{ alignSelf: "flex-start" }}
            onClick={saveRouting} disabled={busy !== null}>Save routing</button>
        </section>
      )}

      <table className="services-table">
        <thead><tr><th>Provider</th><th>Type</th><th>Status</th><th>API key</th><th /></tr></thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id} style={p.active ? { background: "var(--accent-soft)" } : undefined}>
              <td>
                {p.active ? "● " : ""}{p.label}
                <div className="mono" style={{ opacity: 0.55, fontSize: 11 }}>{p.base_url || "set LLM_BASE_URL in Settings"}</div>
              </td>
              <td>
                <span className={`badge ${p.local ? "run" : "off"}`}>{p.local ? "local" : "cloud"}</span>{" "}
                {p.free && <span className="badge ok">free</span>}
              </td>
              <td><span className={`badge ${p.configured ? "ok" : "off"}`}>{p.configured ? "ready" : "needs key"}</span></td>
              <td>
                {p.key_env && IS_TAURI ? (
                  <span className="field-row">
                    <input type="password" placeholder={p.key_env} value={keyInputs[p.id] ?? ""}
                      style={{ maxWidth: 190, padding: "5px 9px", fontSize: 12,
                        background: "var(--bg)", border: "1px solid var(--border)",
                        borderRadius: 7, color: "var(--text)" }}
                      onChange={(e) => setKeyInputs((k) => ({ ...k, [p.id]: e.target.value }))}
                      spellCheck={false} autoComplete="off" />
                    <button className="btn small" disabled={busy === p.id || !keyInputs[p.id]}
                      onClick={() => saveKey(p)}>save</button>
                  </span>
                ) : (
                  <span className="mono" style={{ opacity: 0.5, fontSize: 11 }}>{p.local ? "no key needed" : "—"}</span>
                )}
              </td>
              <td>
                <button className="btn small" disabled={busy === p.id} onClick={() => fetchModels(p)}>
                  {busy === p.id ? "…" : "models"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {models && (
        <div className="logs-modal" onClick={() => setModels(null)}>
          <div className="logs-box" onClick={(e) => e.stopPropagation()}>
            <div className="logs-head">
              <strong>{models.provider.label} — {models.list.length} models (click to activate)</strong>
              <button className="btn small" onClick={() => setModels(null)}>close</button>
            </div>
            <div style={{ overflow: "auto", padding: "10px 14px", display: "flex", flexWrap: "wrap", gap: 8 }}>
              {models.list.length === 0 && <span className="muted">provider reachable, but returned no models</span>}
              {models.list.map((m) => (
                <button key={m} className="chip" onClick={() => selectModel(models.provider, m)}>{m}</button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
