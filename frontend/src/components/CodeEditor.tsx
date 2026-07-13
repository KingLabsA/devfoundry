import { useCallback, useEffect, useRef, useState } from "react";
import {
  downloadUrl, listProjectFiles, ProjectFile, readProjectFile,
  uploadProjectZip, writeProjectFile,
} from "../api/client";

export function CodeEditor({ runId }: { runId: string }) {
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setFiles(await listProjectFiles(runId));
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);

  const open = async (path: string) => {
    try {
      const { content: c, binary } = await readProjectFile(runId, path);
      setSelected(path);
      setContent(binary ? "(binary file — not editable)" : c);
      setDirty(false);
      setStatus("");
    } catch (err) {
      setStatus(String(err));
    }
  };

  const save = async () => {
    if (!selected) return;
    try {
      await writeProjectFile(runId, selected, content);
      setDirty(false);
      setStatus(`Saved ${selected}`);
    } catch (err) {
      setStatus(`Save failed: ${err}`);
    }
  };

  const upload = async (file: File) => {
    try {
      const n = await uploadProjectZip(runId, file);
      setStatus(`Uploaded ${n} files`);
      await refresh();
    } catch (err) {
      setStatus(`Upload failed: ${err}`);
    }
  };

  if (files.length === 0) {
    return (
      <div className="editor-empty">
        <p>No project files yet for this run.</p>
        <div className="editor-actions">
          <button className="btn small" onClick={refresh}>↻ Refresh</button>
          <button className="btn small" onClick={() => fileInput.current?.click()}>⬆ Upload .zip</button>
        </div>
        <input ref={fileInput} type="file" accept=".zip" hidden
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
      </div>
    );
  }

  return (
    <div className="code-editor">
      <div className="editor-sidebar">
        <div className="editor-toolbar">
          <a className="btn small" href={downloadUrl(runId)} download>⬇ Zip</a>
          <button className="btn small" onClick={() => fileInput.current?.click()}>⬆ Zip</button>
          <button className="btn small" onClick={refresh}>↻</button>
          <input ref={fileInput} type="file" accept=".zip" hidden
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        </div>
        <ul className="file-tree">
          {files.map((f) => (
            <li key={f.path}>
              <button className={selected === f.path ? "file-item active" : "file-item"} onClick={() => open(f.path)}>
                <span className="file-name">{f.path}</span>
                <span className="file-size">{f.size}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="editor-main">
        {selected ? (
          <>
            <div className="editor-head">
              <span className="mono">{selected}{dirty ? " ●" : ""}</span>
              <button className="btn small primary" onClick={save} disabled={!dirty}>Save ⌘S</button>
            </div>
            <textarea
              className="editor-textarea"
              value={content}
              spellCheck={false}
              onChange={(e) => { setContent(e.target.value); setDirty(true); }}
              onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); } }}
            />
          </>
        ) : (
          <div className="editor-empty"><p>Select a file to edit.</p></div>
        )}
        {status && <div className="editor-status">{status}</div>}
      </div>
    </div>
  );
}
