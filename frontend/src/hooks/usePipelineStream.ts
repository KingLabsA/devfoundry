import { useCallback, useRef, useState } from "react";
import { createRun, DeployOptions, openRunStream, PipelineEvent, stopRun } from "../api/client";

export function usePipelineStream() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [stage, setStage] = useState<string>("idle");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const start = useCallback(async (idea: string, opts: DeployOptions = {}) => {
    setEvents([]);
    setError(null);
    setStage("queued");
    setRunning(true);
    try {
      const id = await createRun(idea, opts);
      setRunId(id);
      wsRef.current = openRunStream(
        id,
        (e) => {
          setEvents((prev) => [...prev, e]);
          if (e.kind === "status") setStage(e.stage);
          if (e.stage === "failed") setError(e.message);
        },
        () => setRunning(false),
      );
    } catch (err) {
      setError(String(err));
      setRunning(false);
    }
  }, []);

  const stop = useCallback(async () => {
    if (runId) await stopRun(runId);
  }, [runId]);

  return { events, stage, running, error, runId, start, stop };
}
