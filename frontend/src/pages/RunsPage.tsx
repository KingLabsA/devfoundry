import { useEffect, useState } from "react";

interface RunSummary {
  run_id: string;
  idea: string;
  stage: string;
  error: string | null;
}

export function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const resp = await fetch("http://localhost:9100/api/runs");
        if (resp.ok && alive) setRuns(await resp.json());
      } catch {
        if (alive) setRuns(null);
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <div className="page">
      <div className="page-head"><h2>Run History</h2></div>
      {runs === null ? (
        <div className="empty-state">Backend offline — start the stack from the Services page.</div>
      ) : runs.length === 0 ? (
        <div className="empty-state">No runs yet. Forge your first app idea.</div>
      ) : (
        <table className="services-table">
          <thead><tr><th>Run</th><th>Idea</th><th>Stage</th><th>Error</th></tr></thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id}>
                <td className="mono">{r.run_id.slice(0, 8)}</td>
                <td>{r.idea}</td>
                <td><span className={`badge ${r.stage === "done" ? "ok" : r.stage === "failed" ? "err" : "run"}`}>{r.stage}</span></td>
                <td className="mono">{r.error ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
