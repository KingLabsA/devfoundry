import { HealthReport } from "../api/client";

const SERVICES: { key: keyof HealthReport; label: string }[] = [
  { key: "metagpt", label: "MetaGPT" },
  { key: "boltdiy", label: "Bolt.diy" },
  { key: "orc", label: "Orc" },
  { key: "opencode", label: "OpenCode" },
  { key: "superpowers", label: "Superpowers" },
];

export function HealthBar({ health, checked }: { health: HealthReport | null; checked: boolean }) {
  if (!checked) return <div className="health-bar muted">checking services…</div>;
  if (!health) {
    return (
      <div className="health-bar">
        <span className="dot down" /> backend offline — run <code>docker compose up -d</code>
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
