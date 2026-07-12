import { useEffect, useState } from "react";
import { IS_TAURI, getProjectDir, mergeEnv, parseEnv, readEnv, saveEnv, setProjectDir } from "../api/native";

const PROVIDERS = [
  { key: "ANTHROPIC_API_KEY", label: "Anthropic", hint: "sk-ant-…" },
  { key: "OPENAI_API_KEY", label: "OpenAI", hint: "sk-…" },
  { key: "OPENROUTER_API_KEY", label: "OpenRouter", hint: "sk-or-…" },
  { key: "GROQ_API_KEY", label: "Groq", hint: "gsk_…" },
  { key: "GOOGLE_API_KEY", label: "Google AI Studio", hint: "AIza…" },
];

const ENDPOINTS = [
  { key: "METAGPT_URL", label: "MetaGPT" },
  { key: "BOLTDIY_URL", label: "Bolt.diy" },
  { key: "OPENCODE_URL", label: "OpenCode" },
  { key: "ORC_URL", label: "Orc" },
  { key: "SUPERPOWERS_URL", label: "Superpowers" },
];

export function SettingsPage() {
  const [dir, setDir] = useState(getProjectDir());
  const [envText, setEnvText] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
  const [loaded, setLoaded] = useState(false);

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

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (key: string, v: string) => setValues((prev) => ({ ...prev, [key]: v }));

  const save = async () => {
    try {
      await saveEnv(mergeEnv(envText, values));
      setMessage("Saved to .env — restart services (Services → Stop All, Start All) to apply.");
      await load();
    } catch (err) {
      setMessage(`Save failed: ${err}`);
    }
  };

  if (!IS_TAURI) {
    return <div className="page"><div className="empty-state">Settings are available in the desktop app.</div></div>;
  }

  return (
    <div className="page">
      <div className="page-head">
        <h2>Settings</h2>
        <div className="page-actions">
          <button className="btn primary" onClick={save} disabled={!loaded}>Save</button>
        </div>
      </div>
      {message && <div className="notice">{message}</div>}

      <section className="settings-group">
        <h3>Project</h3>
        <label className="field">
          <span>Project directory (contains docker-compose.yml)</span>
          <input value={dir} onChange={(e) => setDir(e.target.value)}
            onBlur={() => { setProjectDir(dir); load(); }} spellCheck={false} />
        </label>
      </section>

      <section className="settings-group">
        <h3>LLM Providers</h3>
        <p className="hint">Keys are stored in the project's <code>.env</code> file and passed to the services as environment variables — never hardcoded.</p>
        {PROVIDERS.map((p) => (
          <label className="field" key={p.key}>
            <span>{p.label}</span>
            <div className="field-row">
              <input
                type={revealed[p.key] ? "text" : "password"}
                value={values[p.key] ?? ""}
                placeholder={p.hint}
                onChange={(e) => set(p.key, e.target.value)}
                spellCheck={false}
                autoComplete="off"
              />
              <button className="btn small" type="button"
                onClick={() => setRevealed((r) => ({ ...r, [p.key]: !r[p.key] }))}>
                {revealed[p.key] ? "hide" : "show"}
              </button>
            </div>
          </label>
        ))}
        <label className="field">
          <span>Custom OpenAI-compatible gateway (base URL)</span>
          <input value={values.LLM_BASE_URL ?? ""} placeholder="http://localhost:3002/v1"
            onChange={(e) => set("LLM_BASE_URL", e.target.value)} spellCheck={false} />
        </label>
        <label className="field">
          <span>Default model</span>
          <input value={values.LLM_MODEL ?? ""} placeholder="claude-sonnet-5"
            onChange={(e) => set("LLM_MODEL", e.target.value)} spellCheck={false} />
        </label>
      </section>

      <section className="settings-group">
        <h3>Service Endpoints</h3>
        {ENDPOINTS.map((s) => (
          <label className="field" key={s.key}>
            <span>{s.label}</span>
            <input value={values[s.key] ?? ""} onChange={(e) => set(s.key, e.target.value)} spellCheck={false} />
          </label>
        ))}
      </section>

      <section className="settings-group">
        <h3>Deployment</h3>
        <p className="hint">Free targets: Netlify (static hosting) and Hugging Face Spaces (CPU). Local: Docker image or zip bundle.</p>
        <label className="field">
          <span>Deploy target</span>
          <select className="btn" style={{ alignSelf: "flex-start" }}
            value={values.DEPLOY_TARGET ?? "auto"}
            onChange={(e) => set("DEPLOY_TARGET", e.target.value)}>
            <option value="auto">auto (Docker → zip)</option>
            <option value="zip">zip bundle (local)</option>
            <option value="docker">Docker image (local)</option>
            <option value="netlify">Netlify (free)</option>
            <option value="hf-spaces">Hugging Face Spaces (free)</option>
            <option value="vercel">Vercel (free hobby)</option>
            <option value="cloudflare-pages">Cloudflare Pages (free)</option>
            <option value="surge">Surge.sh (free)</option>
          </select>
        </label>
        <label className="field">
          <span>Vercel token (vercel.com/account/tokens)</span>
          <input type="password" value={values.VERCEL_TOKEN ?? ""} placeholder="…"
            onChange={(e) => set("VERCEL_TOKEN", e.target.value)} spellCheck={false} autoComplete="off" />
        </label>
        <div className="field-row">
          <label className="field" style={{ flex: 1 }}>
            <span>Cloudflare API token</span>
            <input type="password" value={values.CLOUDFLARE_API_TOKEN ?? ""} placeholder="…"
              onChange={(e) => set("CLOUDFLARE_API_TOKEN", e.target.value)} spellCheck={false} autoComplete="off" />
          </label>
          <label className="field" style={{ flex: 1 }}>
            <span>Cloudflare account ID</span>
            <input value={values.CLOUDFLARE_ACCOUNT_ID ?? ""} placeholder="…"
              onChange={(e) => set("CLOUDFLARE_ACCOUNT_ID", e.target.value)} spellCheck={false} />
          </label>
        </div>
        <div className="field-row">
          <label className="field" style={{ flex: 1 }}>
            <span>Surge login (email)</span>
            <input value={values.SURGE_LOGIN ?? ""} placeholder="you@example.com"
              onChange={(e) => set("SURGE_LOGIN", e.target.value)} spellCheck={false} />
          </label>
          <label className="field" style={{ flex: 1 }}>
            <span>Surge token (npx surge token)</span>
            <input type="password" value={values.SURGE_TOKEN ?? ""} placeholder="…"
              onChange={(e) => set("SURGE_TOKEN", e.target.value)} spellCheck={false} autoComplete="off" />
          </label>
        </div>
        <label className="field">
          <span>Netlify auth token (free account — app.netlify.com/user/applications)</span>
          <input type="password" value={values.NETLIFY_AUTH_TOKEN ?? ""} placeholder="nfp_…"
            onChange={(e) => set("NETLIFY_AUTH_TOKEN", e.target.value)} spellCheck={false} autoComplete="off" />
        </label>
        <label className="field">
          <span>Hugging Face token (free account — hf.co/settings/tokens, write scope)</span>
          <input type="password" value={values.HF_TOKEN ?? ""} placeholder="hf_…"
            onChange={(e) => set("HF_TOKEN", e.target.value)} spellCheck={false} autoComplete="off" />
        </label>
      </section>

      <section className="settings-group">
        <h3>Pipeline</h3>
        <label className="field">
          <span>Workspace directory</span>
          <input value={values.DEVFOUNDRY_WORKSPACE ?? ""} onChange={(e) => set("DEVFOUNDRY_WORKSPACE", e.target.value)} spellCheck={false} />
        </label>
        <label className="field">
          <span>Service timeout (seconds)</span>
          <input value={values.SERVICE_TIMEOUT_SECONDS ?? ""} onChange={(e) => set("SERVICE_TIMEOUT_SECONDS", e.target.value)} spellCheck={false} />
        </label>
      </section>
    </div>
  );
}
