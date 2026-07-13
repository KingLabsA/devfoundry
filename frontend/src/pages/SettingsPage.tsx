import { useEffect, useState } from "react";
import { IS_TAURI, getProjectDir, keychainSet, mergeEnv, parseEnv, readEnv, saveEnv, setProjectDir } from "../api/native";
import { BASE } from "../api/client";
import { THEMES, applyTheme, currentTheme } from "../themes";

const PROVIDERS = [
  { key: "ANTHROPIC_API_KEY", label: "Anthropic", hint: "sk-ant-…" },
  { key: "OPENAI_API_KEY", label: "OpenAI", hint: "sk-…" },
  { key: "OPENROUTER_API_KEY", label: "OpenRouter", hint: "sk-or-…" },
  { key: "GROQ_API_KEY", label: "Groq", hint: "gsk_…" },
  { key: "GOOGLE_API_KEY", label: "Google AI Studio", hint: "AIza…" },
  { key: "FREELLMAPI_KEY", label: "FreeLLMAPI (gateway)", hint: "freellmapi-…" },
];

const ENDPOINTS = [
  { key: "METAGPT_URL", label: "MetaGPT" },
  { key: "BOLTDIY_URL", label: "Bolt.diy" },
  { key: "OPENCODE_URL", label: "OpenCode" },
  { key: "ORC_URL", label: "Orc" },
  { key: "SUPERPOWERS_URL", label: "Superpowers" },
];

type Tab = "general" | "providers" | "deploy" | "research" | "appearance" | "advanced";
const TABS: [Tab, string][] = [
  ["general", "General"], ["providers", "Providers"], ["deploy", "Deployment"],
  ["research", "Research"], ["appearance", "Appearance"], ["advanced", "Advanced"],
];

const PRESET_KEYS = ["LLM_PROVIDER", "LLM_MODEL", "LLM_ROTATION", "DEPLOY_TARGET",
  "LLM_MODEL_SPEC", "LLM_MODEL_CODEGEN", "LLM_MODEL_TASKS", "LLM_MODEL_REFINE"];

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>("general");
  const [dir, setDir] = useState(getProjectDir());
  const [envText, setEnvText] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [theme, setTheme] = useState(currentTheme());
  const [presets, setPresets] = useState<{ name: string; config: Record<string, string> }[]>([]);
  const [presetName, setPresetName] = useState("");

  const load = async () => {
    if (!IS_TAURI) return;
    try {
      const text = await readEnv();
      setEnvText(text);
      setValues(parseEnv(text));
      setLoaded(true);
      setMessage("");
    } catch (err) {
      setLoaded(false);
      setMessage(String(err));
    }
  };

  const loadPresets = async () => {
    try {
      const r = await fetch(`${BASE}/api/presets`);
      if (r.ok) setPresets(await r.json());
    } catch { /* offline */ }
  };

  useEffect(() => { load(); loadPresets(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (key: string, v: string) => setValues((prev) => ({ ...prev, [key]: v }));

  const save = async () => {
    try {
      await saveEnv(mergeEnv(envText, values));
      setMessage("Saved to .env — applies immediately (embedded mode re-reads live).");
      await load();
    } catch (err) {
      setMessage(`Save failed: ${err}`);
    }
  };

  const savePreset = async () => {
    if (!presetName.trim()) return;
    const config = Object.fromEntries(PRESET_KEYS.map((k) => [k, values[k] ?? ""]).filter(([, v]) => v));
    await fetch(`${BASE}/api/presets`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: presetName.trim(), config }),
    });
    setPresetName("");
    setMessage(`Preset '${presetName.trim()}' saved`);
    await loadPresets();
  };

  const applyPreset = async (p: { name: string; config: Record<string, string> }) => {
    setValues((v) => ({ ...v, ...p.config }));
    await saveEnv(mergeEnv(envText, { ...values, ...p.config }));
    setMessage(`Applied preset '${p.name}'`);
    await load();
  };

  const deletePreset = async (name: string) => {
    await fetch(`${BASE}/api/presets/${encodeURIComponent(name)}`, { method: "DELETE" });
    await loadPresets();
  };

  const pickTheme = (id: string) => { applyTheme(id); setTheme(id); };

  const moveSecretsToKeychain = async () => {
    const text = await readEnv();
    const vals = parseEnv(text);
    const secretKeys = Object.keys(vals).filter(
      (k) => vals[k] && (k.endsWith("_KEY") || k.endsWith("_TOKEN")));
    if (secretKeys.length === 0) { setMessage("No secrets in .env to move."); return; }
    let moved = 0;
    const blanked: Record<string, string> = {};
    for (const k of secretKeys) {
      try { await keychainSet(k, vals[k]); blanked[k] = ""; moved++; } catch { /* skip */ }
    }
    await saveEnv(mergeEnv(text, blanked)); // blank them in .env; backend reads Keychain as fallback
    setMessage(`Moved ${moved} secret(s) to the macOS Keychain and cleared them from .env.`);
    await load();
  };

  const secret = (key: string, label: string, hint = "…") => (
    <label className="field" key={key}>
      <span>{label}</span>
      <div className="field-row">
        <input type={revealed[key] ? "text" : "password"} value={values[key] ?? ""} placeholder={hint}
          onChange={(e) => set(key, e.target.value)} spellCheck={false} autoComplete="off" />
        <button className="btn small" type="button"
          onClick={() => setRevealed((r) => ({ ...r, [key]: !r[key] }))}>{revealed[key] ? "hide" : "show"}</button>
      </div>
    </label>
  );

  if (!IS_TAURI) {
    return <div className="page"><div className="empty-state">Settings are available in the desktop app.</div></div>;
  }

  return (
    <div className="page">
      <div className="page-head">
        <h2>Settings</h2>
        <div className="page-actions"><button className="btn primary" onClick={save} disabled={!loaded}>Save</button></div>
      </div>
      <div className="settings-tabs">
        {TABS.map(([id, label]) => (
          <button key={id} className={tab === id ? "tab active" : "tab"} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>
      {message && <div className="notice">{message}</div>}

      {tab === "general" && (
        <section className="settings-group">
          <h3>Project</h3>
          <label className="field">
            <span>Project directory (contains docker-compose.yml)</span>
            <input value={dir} onChange={(e) => setDir(e.target.value)}
              onBlur={() => { setProjectDir(dir); load(); }} spellCheck={false} />
          </label>
          <label className="field"><span>Workspace directory</span>
            <input value={values.DEVFOUNDRY_WORKSPACE ?? ""} onChange={(e) => set("DEVFOUNDRY_WORKSPACE", e.target.value)} spellCheck={false} /></label>
          <label className="field"><span>Service timeout (seconds)</span>
            <input value={values.SERVICE_TIMEOUT_SECONDS ?? ""} onChange={(e) => set("SERVICE_TIMEOUT_SECONDS", e.target.value)} spellCheck={false} /></label>
        </section>
      )}

      {tab === "providers" && (
        <>
          <section className="settings-group">
            <h3>LLM Provider keys</h3>
            <p className="hint">Stored in the project's <code>.env</code>, read live. Manage the active model & 22 providers on the <strong>Models</strong> page.</p>
            {PROVIDERS.map((p) => secret(p.key, p.label, p.hint))}
            <label className="field"><span>Custom OpenAI-compatible gateway (base URL)</span>
              <input value={values.LLM_BASE_URL ?? ""} placeholder="http://localhost:3002/v1"
                onChange={(e) => set("LLM_BASE_URL", e.target.value)} spellCheck={false} /></label>
          </section>
          <section className="settings-group">
            <h3>Service Endpoints (isolated mode)</h3>
            {ENDPOINTS.map((s) => (
              <label className="field" key={s.key}><span>{s.label}</span>
                <input value={values[s.key] ?? ""} onChange={(e) => set(s.key, e.target.value)} spellCheck={false} /></label>
            ))}
          </section>
        </>
      )}

      {tab === "deploy" && (
        <section className="settings-group">
          <h3>Deployment</h3>
          <p className="hint">Free targets: Netlify, HF Spaces, Vercel, Cloudflare Pages, Surge. Local: Docker/zip.</p>
          <label className="field"><span>Deploy target</span>
            <select className="btn" style={{ alignSelf: "flex-start" }} value={values.DEPLOY_TARGET ?? "auto"}
              onChange={(e) => set("DEPLOY_TARGET", e.target.value)}>
              <option value="auto">auto (Docker → zip)</option>
              <option value="zip">zip bundle (local)</option>
              <option value="docker">Docker image (local)</option>
              <option value="netlify">Netlify (free)</option>
              <option value="hf-spaces">Hugging Face Spaces (free)</option>
              <option value="vercel">Vercel (free hobby)</option>
              <option value="cloudflare-pages">Cloudflare Pages (free)</option>
              <option value="surge">Surge.sh (free)</option>
            </select></label>
          {secret("NETLIFY_AUTH_TOKEN", "Netlify token", "nfp_…")}
          {secret("HF_TOKEN", "Hugging Face token", "hf_…")}
          {secret("VERCEL_TOKEN", "Vercel token", "…")}
          <div className="field-row">
            {secret("CLOUDFLARE_API_TOKEN", "Cloudflare API token", "…")}
            <label className="field" style={{ flex: 1 }}><span>Cloudflare account ID</span>
              <input value={values.CLOUDFLARE_ACCOUNT_ID ?? ""} onChange={(e) => set("CLOUDFLARE_ACCOUNT_ID", e.target.value)} spellCheck={false} /></label>
          </div>
          <div className="field-row">
            <label className="field" style={{ flex: 1 }}><span>Surge login (email)</span>
              <input value={values.SURGE_LOGIN ?? ""} onChange={(e) => set("SURGE_LOGIN", e.target.value)} spellCheck={false} /></label>
            {secret("SURGE_TOKEN", "Surge token", "npx surge token")}
          </div>
        </section>
      )}

      {tab === "research" && (
        <section className="settings-group">
          <h3>Deep Research</h3>
          <p className="hint">Search works keyless (local SearXNG → Wikipedia). Add a free key for full web search.</p>
          <label className="field"><span>SearXNG URL (local metasearch)</span>
            <input value={values.SEARXNG_URL ?? ""} placeholder="http://localhost:8082"
              onChange={(e) => set("SEARXNG_URL", e.target.value)} spellCheck={false} /></label>
          {secret("BRAVE_API_KEY", "Brave Search key (free 2k/mo — brave.com/search/api)", "…")}
          {secret("TAVILY_API_KEY", "Tavily key (free tier — tavily.com)", "tvly-…")}
          {secret("JINA_API_KEY", "Jina reader key (optional — jina.ai)", "jina_…")}
        </section>
      )}

      {tab === "appearance" && (
        <section className="settings-group">
          <h3>Theme</h3>
          <p className="hint">Applied instantly and remembered. Also switchable via ⌘K → “Theme:”.</p>
          <div className="theme-grid">
            {THEMES.map((t) => (
              <button key={t.id} className={`theme-swatch ${theme === t.id ? "active" : ""}`} onClick={() => pickTheme(t.id)}>
                <span className="theme-dots">
                  {["--bg", "--panel", "--accent", "--text"].map((v) => (
                    <span key={v} style={{ background: t.vars[v] }} />
                  ))}
                </span>
                {t.label}
              </button>
            ))}
          </div>
        </section>
      )}

      {tab === "advanced" && (
        <>
          <section className="settings-group">
            <h3>Config presets</h3>
            <p className="hint">Save the current provider/model/rotation/deploy config as a reusable preset.</p>
            <div className="field-row">
              <input placeholder="preset name" value={presetName} style={{ maxWidth: 220 }}
                onChange={(e) => setPresetName(e.target.value)} spellCheck={false} />
              <button className="btn primary" onClick={savePreset} disabled={!presetName.trim()}>Save current</button>
            </div>
            {presets.length > 0 && (
              <table className="services-table">
                <tbody>
                  {presets.map((p) => (
                    <tr key={p.name}>
                      <td>{p.name}</td>
                      <td className="mono" style={{ opacity: 0.6 }}>{p.config.LLM_PROVIDER}{p.config.LLM_MODEL ? `:${p.config.LLM_MODEL}` : ""}</td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        <button className="btn small primary" onClick={() => applyPreset(p)}>apply</button>{" "}
                        <button className="btn small" onClick={() => deletePreset(p.name)}>delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          <section className="settings-group">
            <h3>Security — macOS Keychain</h3>
            <p className="hint">Move API keys out of the plaintext <code>.env</code> into the macOS Keychain.
              The backend reads them from the Keychain automatically.</p>
            <button className="btn primary" style={{ alignSelf: "flex-start" }} onClick={moveSecretsToKeychain}>
              🔒 Move secrets to Keychain
            </button>
          </section>

          <section className="settings-group">
            <h3>Raw .env</h3>
            <p className="hint">Full environment file — advanced edits. Save from the button above.</p>
            <textarea className="env-editor" value={envText} onChange={(e) => setEnvText(e.target.value)} spellCheck={false} rows={14} />
          </section>
        </>
      )}
    </div>
  );
}
