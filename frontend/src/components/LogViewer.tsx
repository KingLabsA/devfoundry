import { useEffect, useRef } from "react";
import { PipelineEvent } from "../api/client";

export function LogViewer({ events }: { events: PipelineEvent[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [events.length]);
  return (
    <div className="log-viewer" ref={ref}>
      {events.map((e, i) => (
        <div key={i} className={`log-line ${e.kind}`}>
          <span className="log-ts">{new Date(e.ts).toLocaleTimeString()}</span>
          <span className="log-stage">[{e.stage}]</span>
          <span>{e.message}</span>
        </div>
      ))}
    </div>
  );
}
