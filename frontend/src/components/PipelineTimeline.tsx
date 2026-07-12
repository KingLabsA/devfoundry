import { PipelineEvent } from "../api/client";
import { StageCard } from "./StageCard";

const STAGES = [
  { id: "spec", label: "Specs", tool: "MetaGPT" },
  { id: "codegen", label: "Codebase", tool: "Bolt.diy" },
  { id: "tasks", label: "Tasks", tool: "Orc" },
  { id: "refine", label: "Refinement", tool: "OpenCode" },
  { id: "deploy", label: "Deploy", tool: "Superpowers" },
];

export function PipelineTimeline({ currentStage, events }: { currentStage: string; events: PipelineEvent[] }) {
  const order = STAGES.map((s) => s.id);
  const currentIdx = order.indexOf(currentStage);
  return (
    <div className="timeline">
      {STAGES.map((s, i) => (
        <StageCard
          key={s.id}
          label={s.label}
          tool={s.tool}
          status={
            currentStage === "done" || i < currentIdx ? "done"
            : i === currentIdx ? "active"
            : currentStage === "failed" && i === currentIdx ? "failed"
            : "pending"
          }
          artifacts={events.filter((e) => e.stage === s.id && e.kind === "artifact")}
        />
      ))}
    </div>
  );
}
