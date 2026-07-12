import { useMemo, useState } from "react";
import { IdeaInput } from "./components/IdeaInput";
import { PipelineTimeline } from "./components/PipelineTimeline";
import { LogViewer } from "./components/LogViewer";
import { ArtifactPanel } from "./components/ArtifactPanel";
import { HealthBar } from "./components/HealthBar";
import { usePipelineStream } from "./hooks/usePipelineStream";
import { useHealth } from "./hooks/useHealth";

type Tab = "logs" | "artifacts";

const STAGE_LABELS: Record<string, string> = {
  idle: "Ready",
  queued: "Queued",
  spec: "Writing specifications",
  codegen: "Generating codebase",
  tasks: "Planning tasks",
  refine: "Refining & testing",
  deploy: "Packaging & deploying",
  done: "Complete",
  failed: "Failed",
};

export default function App() {
  const { events, stage, running, error, start } = usePipelineStream();
  const { health, checked } = useHealth();
  const [tab, setTab] = useState<Tab>("logs");

  const artifacts = useMemo(() => events.filter((e) => e.kind === "artifact"), [events]);

  return (
    <div className="app">
      <header className="titlebar">
        <div className="brand">
          <span className="brand-mark">⬢</span>
          <div>
            <h1>DevFoundry</h1>
            <span className="subtitle">Autonomous Software Development Factory</span>
          </div>
        </div>
        <HealthBar health={health} checked={checked} />
      </header>

      <IdeaInput disabled={running} onSubmit={start} />
      {error && <div className="error">⚠ {error}</div>}

      <PipelineTimeline currentStage={stage} events={events} />

      <div className="panel">
        <div className="panel-tabs">
          <button className={tab === "logs" ? "tab active" : "tab"} onClick={() => setTab("logs")}>
            Live Log <span className="count">{events.length}</span>
          </button>
          <button className={tab === "artifacts" ? "tab active" : "tab"} onClick={() => setTab("artifacts")}>
            Artifacts <span className="count">{artifacts.length}</span>
          </button>
        </div>
        {tab === "logs" ? <LogViewer events={events} /> : <ArtifactPanel artifacts={artifacts} />}
      </div>

      <footer className="statusbar">
        <span className={`status-pill ${stage}`}>{STAGE_LABELS[stage] ?? stage}</span>
        {running && <span className="spinner" aria-label="working" />}
        <span className="statusbar-right">DevFoundry v0.1.0</span>
      </footer>
    </div>
  );
}
