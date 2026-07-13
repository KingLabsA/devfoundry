import { PipelineEvent } from "../api/client";

/** Shows the honest build-verify result: did it install, build, and pass tests? */
export function VerificationBadge({ events }: { events: PipelineEvent[] }) {
  const v = [...events].reverse().find((e) => e.payload.artifact === "verification");
  if (!v) return null;
  const p = v.payload as { status?: string; installed?: boolean; builds?: boolean; tests_pass?: boolean | null };
  const status = p.status ?? "unverified";
  const cls = status === "verified" ? "done" : status === "built" ? "spec" : "failed";
  const mark = (b?: boolean | null) => (b === true ? "✓" : b === false ? "✕" : "—");

  return (
    <span className={`verify-badge ${cls}`} title="Real build-verify result">
      {status === "verified" ? "✓ verified" : status === "built" ? "◐ builds" : "○ unverified"}
      <span className="verify-detail">
        install {mark(p.installed)} · build {mark(p.builds)} · tests {mark(p.tests_pass)}
      </span>
    </span>
  );
}
