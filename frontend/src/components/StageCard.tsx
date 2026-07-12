import { PipelineEvent } from "../api/client";

export function StageCard({
  label, tool, icon, status, artifacts,
}: { label: string; tool: string; icon: string; status: string; artifacts: PipelineEvent[] }) {
  return (
    <div className={`stage-card ${status}`}>
      <div className="stage-head">
        <span className="stage-icon">{icon}</span>
        <div>
          <div className="stage-label">{label}</div>
          <div className="stage-tool">{tool}</div>
        </div>
        <span className={`stage-status ${status}`}>
          {status === "done" ? "✓" : status === "active" ? "●" : status === "failed" ? "✕" : "○"}
        </span>
      </div>
      {artifacts.length > 0 && (
        <div className="stage-artifacts">{artifacts.length} artifact{artifacts.length > 1 ? "s" : ""}</div>
      )}
    </div>
  );
}
