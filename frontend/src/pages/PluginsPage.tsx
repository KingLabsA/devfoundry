import { useCallback, useEffect, useState } from "react";
import { IS_TAURI, parseEnv, readEnv } from "../api/native";

const BASE = "http://localhost:9100";

interface McpServer {
  name: string;
  transport: string;
  command?: string;
  args?: string[];
  url?: string;
  status: "connected" | "error";
  tools: number;
  error?: string;
}

interface McpTool { name: string; description?: string }
interface Provider { id: string; label: string; free: boolean; configured: boolean }

// Curated MCP servers. `runner` picks npx (TypeScript) or uvx (Python).
// `needsEnv` keys are pulled from your .env on install so the server gets them.
interface CatalogItem {
  name: string; desc: string; command: string; args: string[];
  cat: string; needsEnv?: string[];
}
const CATALOG: CatalogItem[] = [
  // official reference — TypeScript (npx)
  { name: "filesystem", desc: "Read/write files in an allowed directory", cat: "Files & Data",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"] },
  { name: "memory", desc: "Persistent knowledge-graph memory (RAG-style recall)", cat: "Memory",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-memory"] },
  { name: "sequential-thinking", desc: "Structured step-by-step reasoning", cat: "Reasoning",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-sequential-thinking"] },
  { name: "everything", desc: "Reference server exercising all MCP features", cat: "Dev",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-everything"] },
  // official reference — Python (uvx)
  { name: "fetch", desc: "Fetch and convert web pages to markdown", cat: "Web",
    command: "uvx", args: ["mcp-server-fetch"] },
  { name: "git", desc: "Inspect and operate on git repositories", cat: "Dev",
    command: "uvx", args: ["mcp-server-git"] },
  { name: "time", desc: "Time and timezone conversions", cat: "Utility",
    command: "uvx", args: ["mcp-server-time"] },
  { name: "sqlite", desc: "Query a local SQLite database", cat: "Files & Data",
    command: "uvx", args: ["mcp-server-sqlite", "--db-path", "/tmp/mcp.db"] },
  // popular third-party
  { name: "github", desc: "GitHub repos, issues, PRs, code search", cat: "Dev",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-github"], needsEnv: ["GITHUB_TOKEN"] },
  { name: "brave-search", desc: "Web search via Brave", cat: "Web",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-brave-search"], needsEnv: ["BRAVE_API_KEY"] },
  { name: "tavily", desc: "AI-optimized web search & extract", cat: "Web",
    command: "npx", args: ["-y", "tavily-mcp"], needsEnv: ["TAVILY_API_KEY"] },
  { name: "playwright", desc: "Drive a browser (navigate, click, scrape)", cat: "Web",
    command: "npx", args: ["-y", "@playwright/mcp@latest"] },
  { name: "puppeteer", desc: "Headless Chrome automation", cat: "Web",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-puppeteer"] },
  { name: "postgres", desc: "Query a PostgreSQL database (read-only)", cat: "Files & Data",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/postgres"] },
  { name: "context7", desc: "Up-to-date library docs & code examples", cat: "Dev",
    command: "npx", args: ["-y", "@upstash/context7-mcp"] },
  { name: "n8n", desc: "n8n workflow automation (528 nodes)", cat: "Automation",
    command: "npx", args: ["-y", "n8n-mcp"] },
  { name: "slack", desc: "Post and read Slack messages", cat: "Automation",
    command: "npx", args: ["-y", "@modelcontextprotocol/server-slack"], needsEnv: ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"] },
];

export function PluginsPage() {
  const [servers, setServers] = useState<McpServer[] | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [tools, setTools] = useState<{ server: string; list: McpTool[] } | null>(null);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ name: "", transport: "stdio", command: "", args: "", url: "" });
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([
        fetch(`${BASE}/api/mcp/servers`).then((r) => r.json()),
        fetch(`${BASE}/api/deploy/providers`).then((r) => r.json()),
      ]);
      setServers(s);
      setProviders(p);
    } catch {
      setServers(null);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const addServer = async () => {
    if (!form.name) return;
    setBusy(true);
    setMessage("");
    try {
      const body = form.transport === "http"
        ? { name: form.name, transport: "http", url: form.url }
        : { name: form.name, transport: "stdio", command: form.command, args: form.args.split(" ").filter(Boolean) };
      const resp = await fetch(`${BASE}/api/mcp/servers`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setForm({ name: "", transport: "stdio", command: "", args: "", url: "" });
      setMessage(`Added ${body.name}`);
      await refresh();
    } catch (err) {
      setMessage(`Add failed: ${err}`);
    } finally {
      setBusy(false);
    }
  };

  const removeServer = async (name: string) => {
    await fetch(`${BASE}/api/mcp/servers/${encodeURIComponent(name)}`, { method: "DELETE" });
    await refresh();
  };

  const installFromCatalog = async (item: CatalogItem) => {
    setBusy(true);
    try {
      const env: Record<string, string> = {};
      const missing: string[] = [];
      if (item.needsEnv && IS_TAURI) {
        const values = parseEnv(await readEnv());
        for (const k of item.needsEnv) {
          if (values[k]) env[k] = values[k];
          else missing.push(k);
        }
      }
      const resp = await fetch(`${BASE}/api/mcp/servers`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: item.name, transport: "stdio", command: item.command,
                               args: item.args, env }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setMessage(missing.length
        ? `Installed ${item.name} — add ${missing.join(", ")} in Settings for it to connect`
        : `Installed ${item.name}`);
      await refresh();
    } catch (err) {
      setMessage(`Install failed: ${err}`);
    } finally {
      setBusy(false);
    }
  };

  const showTools = async (name: string) => {
    try {
      const resp = await fetch(`${BASE}/api/mcp/servers/${encodeURIComponent(name)}/tools`);
      if (!resp.ok) throw new Error(await resp.text());
      setTools({ server: name, list: await resp.json() });
    } catch (err) {
      setMessage(`Tools failed: ${err}`);
    }
  };

  if (servers === null) {
    return <div className="page"><div className="empty-state">Backend offline — plugins load once services are running.</div></div>;
  }

  return (
    <div className="page">
      <div className="page-head"><h2>Plugins — MCP Servers</h2>
        <div className="page-actions"><button className="btn" onClick={refresh}>↻ Refresh</button></div>
      </div>
      {message && <div className="notice">{message}</div>}

      <section className="settings-group">
        <h3>Plugin catalog — {CATALOG.length} servers, one-click install</h3>
        <p className="hint">Model Context Protocol servers via <code>npx</code> (Node) or <code>uvx</code> (Python).
          Servers marked 🔑 read their key from your <code>.env</code> (set it in Settings).</p>
        <div className="catalog-grid">
          {CATALOG.map((item) => {
            const installed = (servers ?? []).some((s) => s.name === item.name);
            return (
              <div className="catalog-card" key={item.name}>
                <div className="catalog-name">{item.name} <span className="catalog-cat">{item.cat}</span></div>
                <div className="catalog-desc">{item.desc}{item.needsEnv ? " 🔑" : ""}</div>
                <button className="btn small primary" disabled={busy || installed}
                  onClick={() => installFromCatalog(item)}>
                  {installed ? "✓ installed" : `install (${item.command})`}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="settings-group">
        <h3>Add custom MCP server</h3>
        <p className="hint">Connect any Model Context Protocol server — stdio command (e.g. <code>npx -y @modelcontextprotocol/server-filesystem /path</code>) or HTTP endpoint.</p>
        <div className="field-row">
          <input placeholder="name" value={form.name} style={{ maxWidth: 160 }}
            onChange={(e) => setForm({ ...form, name: e.target.value })} spellCheck={false} />
          <select value={form.transport} className="btn"
            onChange={(e) => setForm({ ...form, transport: e.target.value })}>
            <option value="stdio">stdio</option>
            <option value="http">http</option>
          </select>
          {form.transport === "stdio" ? (
            <>
              <input placeholder="command (e.g. npx)" value={form.command} style={{ maxWidth: 180 }}
                onChange={(e) => setForm({ ...form, command: e.target.value })} spellCheck={false} />
              <input placeholder="args" value={form.args}
                onChange={(e) => setForm({ ...form, args: e.target.value })} spellCheck={false} />
            </>
          ) : (
            <input placeholder="https://host/mcp" value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })} spellCheck={false} />
          )}
          <button className="btn primary" onClick={addServer} disabled={busy || !form.name}>Add</button>
        </div>
      </section>

      {servers.length > 0 && (
        <table className="services-table">
          <thead><tr><th>Server</th><th>Transport</th><th>Status</th><th>Tools</th><th /></tr></thead>
          <tbody>
            {servers.map((s) => (
              <tr key={s.name}>
                <td>{s.name}<div className="mono" style={{ opacity: 0.6 }}>{s.url || `${s.command} ${(s.args || []).join(" ")}`}</div></td>
                <td className="mono">{s.transport}</td>
                <td><span className={`badge ${s.status === "connected" ? "ok" : "err"}`} title={s.error}>{s.status}</span></td>
                <td>{s.tools}</td>
                <td>
                  <button className="btn small" onClick={() => showTools(s.name)}>tools</button>{" "}
                  <button className="btn small" onClick={() => removeServer(s.name)}>remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="page-head"><h2>Deployment Providers</h2></div>
      <table className="services-table">
        <thead><tr><th>Provider</th><th>Cost</th><th>Status</th></tr></thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id}>
              <td>{p.label}</td>
              <td><span className="badge ok">free</span></td>
              <td><span className={`badge ${p.configured ? "ok" : "off"}`}>{p.configured ? "ready" : "needs token (Settings)"}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">Pick the active target in Settings → Deployment. Netlify and Hugging Face Spaces are free-tier cloud deploys; Docker/zip are local.</p>

      {tools && (
        <div className="logs-modal" onClick={() => setTools(null)}>
          <div className="logs-box" onClick={(e) => e.stopPropagation()}>
            <div className="logs-head">
              <strong>{tools.server} — {tools.list.length} tools</strong>
              <button className="btn small" onClick={() => setTools(null)}>close</button>
            </div>
            <pre>{tools.list.map((t) => `${t.name}\n  ${t.description ?? ""}`).join("\n\n") || "(no tools)"}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
