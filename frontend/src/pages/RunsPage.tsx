import { useCallback, useEffect, useState } from "react";
import { BASE, PipelineEvent } from "../api/client";

interface RunRow {
  run_id: string;
  idea: string;
  stage: string;
  error: string | null;
  created_at: string;
}

const badgeClass = (stage: string) =>
  stage === "done" ? "ok" : stage === "failed" ? "err" : "run";

export function RunsPage() {
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [selected, setSelected] = useState<RunRow | null>(null);
  const [events, setEvents] = useState<PipelineEvent[]>([]);

  const refresh = useCallback(async () => {
    try {
      const resp = await fetch(`${BASE}/api/runs`);
      if (resp.ok) setRuns(await resp.json());
    } catch {
      setRuns(null);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 6000);
    return () => clearInterval(id);
  }, [refresh]);

  const openRun = async (r: RunRow) => {
    setSelected(r);
    try {
      const resp = await fetch(`${BASE}/api/runs/${r.run_id}/events`);
      setEvents(resp.ok ? await resp.json() : []);
    } catch {
      setEvents([]);
    }
  };

  const remove = async (r: RunRow) => {
    await fetch(`${BASE}/api/runs/${r.run_id}`, { method: "DELETE" });
    if (selected?.run_id === r.run_id) setSelected(null);
    await refresh();
  };

  if (runs === null) {
    return <div className="page"><div className="empty-state">Backend offline — history loads once services are running.</div></div>;
  }

  return (
    <div className="page">
      <div className="page-head">
        <h2>Build History <span className="count">{runs.length}</span></h2>
        <div className="page-actions"><button className="btn" onClick={refresh}>↻ Refresh</button></div>
      </div>
      {runs.length === 0 ? (
        <div className="empty-state">No builds yet. Forge your first app idea — history is saved and survives restarts.</div>
      ) : (
        <table className="services-table">
          <thead><tr><th>When</th><th>Idea</th><th>Stage</th><th /></tr></thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id}>
                <td className="mono">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td>
                <td>{r.idea}</td>
                <td><span className={`badge ${badgeClass(r.stage)}`}>{r.stage}</span></td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button className="btn small" onClick={() => openRun(r)}>view</button>{" "}
                  <button className="btn small" onClick={() => remove(r)}>delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div className="logs-modal" onClick={() => setSelected(null)}>
          <div className="logs-box" onClick={(e) => e.stopPropagation()} style={{ width: "min(900px, 92vw)" }}>
            <div className="logs-head">
              <strong>{selected.idea}</strong>
              <button className="btn small" onClick={() => setSelected(null)}>close</button>
            </div>
            <div className="log-viewer" style={{ maxHeight: "60vh" }}>
              {events.length === 0 && <div className="muted">No recorded events.</div>}
              {events.map((e, i) => (
                <div key={i} className={`log-line ${e.kind}`}>
                  <span className="log-ts">{new Date(e.ts).toLocaleTimeString()}</span>
                  <span className="log-stage">[{e.stage}]</span>
                  <span>{e.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
