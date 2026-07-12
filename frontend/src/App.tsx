import { IdeaInput } from "./components/IdeaInput";
import { PipelineTimeline } from "./components/PipelineTimeline";
import { LogViewer } from "./components/LogViewer";
import { usePipelineStream } from "./hooks/usePipelineStream";

export default function App() {
  const { events, stage, running, error, start } = usePipelineStream();

  return (
    <div className="app">
      <header>
        <h1>DevFoundry</h1>
        <span className="subtitle">Autonomous Software Development Factory</span>
      </header>
      <IdeaInput disabled={running} onSubmit={start} />
      {error && <div className="error">{error}</div>}
      <PipelineTimeline currentStage={stage} events={events} />
      <LogViewer events={events} />
    </div>
  );
}
