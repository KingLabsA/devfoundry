import { useCallback, useEffect, useRef, useState } from "react";
import { listProjectFiles, readProjectFile } from "../api/client";

/**
 * Live canvas: renders the generated app's HTML in a sandboxed iframe, inlining
 * its local CSS/JS so a static frontend previews without a server. If a
 * deployment URL exists, offers to load that instead.
 */
export function CanvasPreview({ runId, deployUrl }: { runId: string; deployUrl?: string }) {
  const [html, setHtml] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [mode, setMode] = useState<"inline" | "deployed">(deployUrl ? "deployed" : "inline");
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const buildInline = useCallback(async () => {
    setStatus("Building preview…");
    const files = await listProjectFiles(runId);
    const htmlFile = files.find((f) => /(^|\/)(index|public\/index)\.html$/.test(f.path))
      || files.find((f) => f.path.endsWith(".html"));
    if (!htmlFile) {
      setHtml(null);
      setStatus("No HTML entry point found — this project needs a dev server (try the deployed URL).");
      return;
    }
    let doc = (await readProjectFile(runId, htmlFile.path)).content;
    const dir = htmlFile.path.includes("/") ? htmlFile.path.replace(/\/[^/]*$/, "/") : "";

    // Inline local <link rel=stylesheet> and <script src>
    for (const f of files) {
      if (f.path.endsWith(".css")) {
        const css = (await readProjectFile(runId, f.path)).content;
        const name = f.path.replace(dir, "");
        doc = doc.replace(new RegExp(`<link[^>]*href=["'][^"']*${name}["'][^>]*>`, "g"),
          `<style>${css}</style>`);
      }
    }
    for (const f of files) {
      if (f.path.endsWith(".js") && !f.path.includes("node_modules")) {
        const js = (await readProjectFile(runId, f.path)).content;
        const name = f.path.replace(dir, "");
        doc = doc.replace(new RegExp(`<script[^>]*src=["'][^"']*${name}["'][^>]*></script>`, "g"),
          `<script>${js}<\/script>`);
      }
    }
    setHtml(doc);
    setStatus("");
  }, [runId]);

  useEffect(() => {
    if (mode === "inline") buildInline();
  }, [mode, buildInline]);

  return (
    <div className="canvas-preview">
      <div className="canvas-toolbar">
        <div className="canvas-tabs">
          <button className={mode === "inline" ? "tab active" : "tab"} onClick={() => setMode("inline")}>Live preview</button>
          {deployUrl && (
            <button className={mode === "deployed" ? "tab active" : "tab"} onClick={() => setMode("deployed")}>Deployed site</button>
          )}
        </div>
        {mode === "inline" && <button className="btn small" onClick={buildInline}>↻ Rebuild</button>}
        {mode === "deployed" && deployUrl && <a className="btn small" href={deployUrl} target="_blank" rel="noreferrer">Open ↗</a>}
      </div>
      <div className="canvas-frame">
        {mode === "deployed" && deployUrl ? (
          <iframe title="deployed" src={deployUrl} sandbox="allow-scripts allow-same-origin allow-forms" />
        ) : html ? (
          <iframe title="preview" ref={iframeRef} srcDoc={html} sandbox="allow-scripts allow-forms" />
        ) : (
          <div className="empty-state">{status || "Nothing to preview yet."}</div>
        )}
      </div>
      {status && mode === "inline" && html && <div className="editor-status">{status}</div>}
    </div>
  );
}
