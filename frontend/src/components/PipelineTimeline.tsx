import { PipelineEvent } from "../api/client";
import { StageCard } from "./StageCard";

const STAGES = [
  { id: "spec", label: "Specs", tool: "MetaGPT", icon: "📋" },
  { id: "codegen", label: "Codebase", tool: "Bolt.diy", icon: "⚡" },
  { id: "tasks", label: "Tasks", tool: "Orc", icon: "🗂" },
  { id: "refine", label: "Refinement", tool: "OpenCode", icon: "🔧" },
  { id: "deploy", label: "Deploy", tool: "Superpowers", icon: "🚀" },
];

export function PipelineTimeline({ currentStage, events }: { currentStage: string; events: PipelineEvent[] }) {
  const order = STAGES.map((s) => s.id);
  const currentIdx = order.indexOf(currentStage);
  const failed = currentStage === "failed";
  const done = currentStage === "done";

  return (
    <div className="timeline">
      {STAGES.map((s, i) => {
        const status = done || (currentIdx >= 0 && i < currentIdx) ? "done"
          : i === currentIdx ? (failed ? "failed" : "active")
          : "pending";
        return (
          <div className="timeline-cell" key={s.id}>
            <StageCard
              label={s.label}
              tool={s.tool}
              icon={s.icon}
              status={status}
              artifacts={events.filter((e) => e.stage === s.id && e.kind === "artifact")}
            />
            {i < STAGES.length - 1 && <div className={`connector ${status === "done" ? "done" : ""}`} />}
          </div>
        );
      })}
    </div>
  );
}
