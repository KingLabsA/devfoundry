import { useCallback, useEffect, useRef, useState } from "react";
import { listProjectFiles, readProjectFile } from "../api/client";
import { IS_TAURI, startDevServer, stopDevServer } from "../api/native";

/**
 * Canvas: three preview modes.
 * - "live"     — spawn the project's real dev server (npm run dev) and iframe it (full app, HMR)
 * - "static"   — inline HTML/CSS/JS for a serverless static preview
 * - "deployed" — the deployment URL, if any
 */
export function CanvasPreview({ runId, projectDir, deployUrl }: {
  runId: string;
  projectDir?: string;
  deployUrl?: string;
}) {
  const [mode, setMode] = useState<"live" | "static" | "deployed">(deployUrl ? "deployed" : "static");
  const [html, setHtml] = useState<string | null>(null);
  const [devPort, setDevPort] = useState<number | null>(null);
  const [starting, setStarting] = useState(false);
  const [status, setStatus] = useState("");

  const buildInline = useCallback(async () => {
    setStatus("Building static preview…");
    const files = await listProjectFiles(runId);
    const htmlFile = files.find((f) => /(^|\/)(index|public\/index)\.html$/.test(f.path))
      || files.find((f) => f.path.endsWith(".html"));
    if (!htmlFile) {
      setHtml(null);
      setStatus("No static HTML entry — use “Live server” to run the app (needs npm).");
      return;
    }
    let doc = (await readProjectFile(runId, htmlFile.path)).content;
    const dir = htmlFile.path.includes("/") ? htmlFile.path.replace(/\/[^/]*$/, "/") : "";
    for (const f of files) {
      if (f.path.endsWith(".css")) {
        const css = (await readProjectFile(runId, f.path)).content;
        const name = f.path.replace(dir, "");
        doc = doc.replace(new RegExp(`<link[^>]*href=["'][^"']*${name}["'][^>]*>`, "g"), `<style>${css}</style>`);
      }
    }
    for (const f of files) {
      if (f.path.endsWith(".js") && !f.path.includes("node_modules")) {
        const js = (await readProjectFile(runId, f.path)).content;
        const name = f.path.replace(dir, "");
        doc = doc.replace(new RegExp(`<script[^>]*src=["'][^"']*${name}["'][^>]*></script>`, "g"), `<script>${js}<\/script>`);
      }
    }
    setHtml(doc);
    setStatus("");
  }, [runId]);

  const runLive = async () => {
    if (!projectDir) { setStatus("No project directory for this run."); return; }
    setStarting(true);
    setStatus("Starting dev server (first run installs deps)…");
    try {
      const port = await startDevServer(projectDir);
      // give the dev server a moment to boot
      await new Promise((r) => setTimeout(r, 4000));
      setDevPort(port);
      setStatus("");
    } catch (err) {
      setStatus(`${err}`);
    } finally {
      setStarting(false);
    }
  };

  const stopLive = useCallback(async () => {
    if (projectDir) { try { await stopDevServer(projectDir); } catch { /* ignore */ } }
    setDevPort(null);
  }, [projectDir]);

  useEffect(() => {
    if (mode === "static") buildInline();
  }, [mode, buildInline]);

  // stop the dev server when leaving the page/unmounting
  useEffect(() => () => { stopLive(); }, [stopLive]);

  return (
    <div className="canvas-preview">
      <div className="canvas-toolbar">
        <div className="canvas-tabs">
          {IS_TAURI && <button className={mode === "live" ? "tab active" : "tab"} onClick={() => setMode("live")}>Live server</button>}
          <button className={mode === "static" ? "tab active" : "tab"} onClick={() => setMode("static")}>Static</button>
          {deployUrl && <button className={mode === "deployed" ? "tab active" : "tab"} onClick={() => setMode("deployed")}>Deployed</button>}
        </div>
        {mode === "static" && <button className="btn small" onClick={buildInline}>↻ Rebuild</button>}
        {mode === "live" && (devPort
          ? <span style={{ display: "flex", gap: 8 }}>
              <a className="btn small" href={`http://localhost:${devPort}`} target="_blank" rel="noreferrer">Open ↗</a>
              <button className="btn small" onClick={stopLive}>■ Stop server</button>
            </span>
          : <button className="btn small primary" onClick={runLive} disabled={starting}>{starting ? "starting…" : "▶ Run dev server"}</button>)}
        {mode === "deployed" && deployUrl && <a className="btn small" href={deployUrl} target="_blank" rel="noreferrer">Open ↗</a>}
      </div>
      <div className="canvas-frame">
        {mode === "deployed" && deployUrl ? (
          <iframe title="deployed" src={deployUrl} sandbox="allow-scripts allow-same-origin allow-forms" />
        ) : mode === "live" && devPort ? (
          <iframe title="live" src={`http://localhost:${devPort}`} sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
        ) : mode === "static" && html ? (
          <iframe title="preview" srcDoc={html} sandbox="allow-scripts allow-forms" />
        ) : (
          <div className="empty-state">{status || (mode === "live" ? "Run the dev server to preview the live app." : "Nothing to preview yet.")}</div>
        )}
      </div>
      {status && <div className="editor-status">{status}</div>}
    </div>
  );
}
