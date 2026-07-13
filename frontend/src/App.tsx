import { useMemo, useState } from "react";
import { IdeaInput } from "./components/IdeaInput";
import { PipelineTimeline } from "./components/PipelineTimeline";
import { LogViewer } from "./components/LogViewer";
import { ArtifactPanel } from "./components/ArtifactPanel";
import { CodeEditor } from "./components/CodeEditor";
import { CanvasPreview } from "./components/CanvasPreview";
import { DeployBar } from "./components/DeployBar";
import { HealthBar } from "./components/HealthBar";
import { Sidebar, Page } from "./components/Sidebar";
import { ServicesPage } from "./pages/ServicesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { RunsPage } from "./pages/RunsPage";
import { PluginsPage } from "./pages/PluginsPage";
import { ModelsPage } from "./pages/ModelsPage";
import { GatewayPage } from "./pages/GatewayPage";
import { ResearchPage } from "./pages/ResearchPage";
import { CommandPalette } from "./components/CommandPalette";
import { usePipelineStream } from "./hooks/usePipelineStream";
import { useHealth } from "./hooks/useHealth";

type Tab = "logs" | "artifacts" | "code" | "canvas";

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
  const { events, stage, running, error, runId, start, stop } = usePipelineStream();
  const { health, checked } = useHealth();
  const [tab, setTab] = useState<Tab>("logs");
  const [page, setPage] = useState<Page>("forge");
  const [deployTarget, setDeployTarget] = useState("auto");
  const [deployDomain, setDeployDomain] = useState("");

  const artifacts = useMemo(() => events.filter((e) => e.kind === "artifact"), [events]);
  const deployUrl = useMemo(() => {
    const dep = [...artifacts].reverse().find((e) => e.payload.artifact === "deployment");
    return (dep?.payload.url as string) || undefined;
  }, [artifacts]);
  const hasProject = stage === "done" || stage === "failed" || tab === "code";

  const submit = (idea: string) =>
    start(idea, { deploy_target: deployTarget, custom_domain: deployDomain });

  return (
    <div className="shell">
      <Sidebar page={page} onNavigate={setPage} servicesUp={health?.backend === "ok"} />

      <div className="app">
        <header className="titlebar">
          <div className="brand">
            <span className="brand-mark">⬢</span>
            <div>
              <h1>DevFoundry</h1>
              <span className="subtitle">Autonomous Software Development Factory</span>
            </div>
          </div>
          <HealthBar health={health} checked={checked} onOpenServices={() => setPage("services")} />
        </header>

        {page === "forge" && (
          <>
            <IdeaInput disabled={running} onSubmit={submit} running={running} onStop={stop} />
            <DeployBar
              target={deployTarget} domain={deployDomain}
              onTarget={setDeployTarget} onDomain={setDeployDomain}
              runId={stage === "done" || stage === "failed" ? runId : null}
            />
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
                <button className={tab === "code" ? "tab active" : "tab"} onClick={() => setTab("code")}>
                  Code
                </button>
                <button className={tab === "canvas" ? "tab active" : "tab"} onClick={() => setTab("canvas")}>
                  Canvas
                </button>
              </div>
              {tab === "logs" && <LogViewer events={events} />}
              {tab === "artifacts" && <ArtifactPanel artifacts={artifacts} />}
              {tab === "code" && (runId ? <CodeEditor runId={runId} /> : <div className="empty-state">Forge an idea to browse and edit its code.</div>)}
              {tab === "canvas" && (runId ? <CanvasPreview runId={runId} deployUrl={deployUrl} /> : <div className="empty-state">Forge an idea to preview the app.</div>)}
            </div>
          </>
        )}
        {page === "research" && <ResearchPage />}
        {page === "runs" && <RunsPage />}
        {page === "models" && <ModelsPage />}
        {page === "plugins" && <PluginsPage />}
        {page === "gateway" && <GatewayPage />}
        {page === "services" && <ServicesPage health={health} />}
        {page === "settings" && <SettingsPage />}
        <CommandPalette onNavigate={setPage} />

        <footer className="statusbar">
          <span className={`status-pill ${stage}`}>{STAGE_LABELS[stage] ?? stage}</span>
          {running && <span className="spinner" aria-label="working" />}
          {running && <button className="btn small stop-btn" onClick={stop}>■ Stop</button>}
          <span className="statusbar-right">{hasProject && runId ? `run ${runId.slice(0, 8)}` : "DevFoundry v0.1.0"}</span>
        </footer>
      </div>
    </div>
  );
}
