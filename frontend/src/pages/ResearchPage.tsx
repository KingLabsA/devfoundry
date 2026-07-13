import { useRef, useState } from "react";
import { BASE } from "../api/client";
import { Markdown } from "../components/Markdown";

interface Source { n?: number; title: string; url: string }
interface Result { report: string; sources: Source[]; queries: string[] }

export function ResearchPage() {
  const [question, setQuestion] = useState("");
  const [depth, setDepth] = useState(4);
  const [steps, setSteps] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const run = () => {
    if (question.trim().length < 8 || running) return;
    setSteps([]); setResult(null); setError(""); setRunning(true);
    const ws = new WebSocket(`${BASE.replace("http", "ws")}/api/research/ws`);
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ question: question.trim(), depth, read_top: 3 }));
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.type === "step") setSteps((s) => [...s, msg.message]);
      else if (msg.type === "result") { setResult(msg); setRunning(false); }
      else if (msg.type === "error") { setError(msg.message); setRunning(false); }
    };
    ws.onclose = () => setRunning(false);
    ws.onerror = () => { setError("connection failed"); setRunning(false); };
  };

  const copyReport = () => result && navigator.clipboard.writeText(result.report);

  const downloadReport = () => {
    if (!result) return;
    const md = `# ${question}\n\n${result.report}\n`;
    const blob = new Blob([md], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `research-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="page">
      <div className="page-head"><h2>Deep Research</h2>
        {result && (
          <div className="page-actions">
            <button className="btn small" onClick={copyReport}>Copy</button>
            <button className="btn small" onClick={downloadReport}>Download .md</button>
          </div>
        )}
      </div>
      <p className="hint">Multi-step web research → cited report. Uses a keyless search chain
        (SearXNG → Wikipedia; add a free Brave/Tavily key in Settings for full web search) and the active LLM.</p>

      <div className="research-input">
        <textarea rows={2} value={question} placeholder="Ask a research question…"
          disabled={running} onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run(); }} />
        <div className="research-controls">
          <label className="hint">depth
            <select className="btn" value={depth} onChange={(e) => setDepth(Number(e.target.value))} disabled={running}>
              {[2, 3, 4, 6].map((d) => <option key={d} value={d}>{d} queries</option>)}
            </select>
          </label>
          <button className="btn primary" onClick={run} disabled={running || question.trim().length < 8}>
            {running ? "Researching…" : "Research"}
          </button>
        </div>
      </div>

      {error && <div className="error">⚠ {error}</div>}

      {(steps.length > 0 || running) && (
        <div className="research-steps">
          {steps.map((s, i) => <div key={i} className="research-step">{i === steps.length - 1 && running ? "▸ " : "✓ "}{s}</div>)}
          {running && <span className="spinner" />}
        </div>
      )}

      {result && (
        <div className="research-report">
          <div className="report-body"><Markdown>{result.report}</Markdown></div>
          {result.sources.length > 0 && (
            <div className="report-sources">
              <h4>Sources</h4>
              <ol>
                {result.sources.map((s, i) => (
                  <li key={i}><a href={s.url} target="_blank" rel="noreferrer">{s.title || s.url}</a></li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
