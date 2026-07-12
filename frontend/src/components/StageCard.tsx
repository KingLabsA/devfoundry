import { PipelineEvent } from "../api/client";

export function StageCard({
  label, tool, status, artifacts,
}: { label: string; tool: string; status: string; artifacts: PipelineEvent[] }) {
  return (
    <div className={`stage-card ${status}`}>
      <div className="stage-label">{label}</div>
      <div className="stage-tool">{tool}</div>
      <div className="stage-artifacts">
        {artifacts.map((a, i) => (
          <details key={i}>
            <summary>{String(a.payload.artifact ?? "artifact")}</summary>
            <pre>{JSON.stringify(a.payload, null, 2).slice(0, 4000)}</pre>
          </details>
        ))}
      </div>
    </div>
  );
}
