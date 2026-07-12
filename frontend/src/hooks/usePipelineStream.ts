import { useCallback, useRef, useState } from "react";
import { createRun, openRunStream, PipelineEvent } from "../api/client";

export function usePipelineStream() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [stage, setStage] = useState<string>("idle");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const start = useCallback(async (idea: string) => {
    setEvents([]);
    setError(null);
    setRunning(true);
    try {
      const runId = await createRun(idea);
      wsRef.current = openRunStream(
        runId,
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

  return { events, stage, running, error, start };
}
