import { useState } from "react";
import { PipelineEvent } from "../api/client";

export function ArtifactPanel({ artifacts }: { artifacts: PipelineEvent[] }) {
  const [selected, setSelected] = useState(0);

  if (artifacts.length === 0) {
    return <div className="empty-state">Artifacts produced by each stage will appear here.</div>;
  }
  const current = artifacts[Math.min(selected, artifacts.length - 1)];

  return (
    <div className="artifact-panel">
      <ul className="artifact-list">
        {artifacts.map((a, i) => (
          <li key={i}>
            <button className={i === selected ? "artifact-item active" : "artifact-item"} onClick={() => setSelected(i)}>
              <span className="artifact-name">{String(a.payload.artifact ?? "artifact")}</span>
              <span className="artifact-stage">{a.stage}</span>
            </button>
          </li>
        ))}
      </ul>
      <pre className="artifact-body">
        {typeof current.payload.content === "string" && current.payload.content
          ? current.payload.content
          : JSON.stringify(current.payload, null, 2)}
      </pre>
    </div>
  );
}
