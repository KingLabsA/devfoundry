import { useState } from "react";
import { HealthReport } from "../api/client";
import { IS_TAURI, ensureStackUp } from "../api/native";

const SERVICES: { key: keyof HealthReport; label: string }[] = [
  { key: "metagpt", label: "MetaGPT" },
  { key: "boltdiy", label: "Bolt.diy" },
  { key: "orc", label: "Orc" },
  { key: "opencode", label: "OpenCode" },
  { key: "superpowers", label: "Superpowers" },
];

export function HealthBar({ health, checked, onOpenServices }: {
  health: HealthReport | null;
  checked: boolean;
  onOpenServices: () => void;
}) {
  const [starting, setStarting] = useState(false);
  const [progress, setProgress] = useState("");
  const [failed, setFailed] = useState(false);

  const startAll = async () => {
    setStarting(true);
    setFailed(false);
    try {
      await ensureStackUp(setProgress);
    } catch (err) {
      setProgress(String(err));
      setFailed(true);
      onOpenServices();
    } finally {
      setStarting(false);
    }
  };

  if (!checked) return <div className="health-bar muted">checking services…</div>;

  if (!health) {
    return (
      <div className="health-bar">
        <span className="dot down" /> {starting && progress ? progress : "services offline"}
        {IS_TAURI && (
          <button className="btn small primary" onClick={startAll} disabled={starting}>
            {starting ? "starting…" : "▶ Start services"}
          </button>
        )}
        {failed && <button className="btn small" onClick={onOpenServices} title={progress}>details</button>}
      </div>
    );
  }
  return (
    <div className="health-bar">
      <span className="health-item"><span className="dot up" /> backend</span>
      {SERVICES.map((s) => (
        <span key={s.key} className="health-item">
          <span className={`dot ${health[s.key] ? "up" : "down"}`} /> {s.label}
        </span>
      ))}
    </div>
  );
}
