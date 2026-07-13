import { useState } from "react";
import { PipelineEvent } from "../api/client";
import { Markdown } from "./Markdown";

// Doc artifacts are markdown; the rest render as JSON/text.
const DOC_ARTIFACTS = new Set(["prd", "architecture", "api_spec"]);

export function ArtifactPanel({ artifacts }: { artifacts: PipelineEvent[] }) {
  const [selected, setSelected] = useState(0);

  if (artifacts.length === 0) {
    return <div className="empty-state">Artifacts produced by each stage will appear here.</div>;
  }
  const current = artifacts[Math.min(selected, artifacts.length - 1)];
  const name = String(current.payload.artifact ?? "artifact");
  const content = current.payload.content;
  const isDoc = DOC_ARTIFACTS.has(name) && typeof content === "string" && content;

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
      {isDoc ? (
        <div className="artifact-body"><Markdown>{content as string}</Markdown></div>
      ) : (
        <pre className="artifact-body">
          {typeof content === "string" && content ? content : JSON.stringify(current.payload, null, 2)}
        </pre>
      )}
    </div>
  );
}
