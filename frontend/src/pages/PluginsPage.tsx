import { useCallback, useEffect, useState } from "react";

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
        <h3>Add MCP server</h3>
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
