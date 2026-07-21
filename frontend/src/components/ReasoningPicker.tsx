const MODES: { id: string; label: string; hint: string }[] = [
  { id: "fast", label: "⚡ Fast", hint: "Single-shot — cheapest & quickest (1× LLM cost)" },
  { id: "balanced", label: "⚖ Balanced", hint: "ToT design: 3 candidate briefs → judge picks the best (~+3 calls)" },
  { id: "deep", label: "🧠 Deep", hint: "Balanced + Self-MoA codegen: N samples from your best model, judge ranks (~3× codegen cost)" },
  { id: "ensemble", label: "🎭 Ensemble", hint: "Balanced + MoA: proposals from DISTINCT providers, judge ranks (~3× cost, max diversity)" },
  { id: "auto", label: "🧭 Auto", hint: "Complexity probe routes to fast/balanced/deep/ensemble (entropy-inspired)" },
];

export function ReasoningPicker({ mode, onChange }: { mode: string; onChange: (m: string) => void }) {
  return (
    <div className="reasoning-picker">
      <span className="skill-label">🧩 Reasoning</span>
      {MODES.map((m) => (
        <button key={m.id} title={m.hint}
          className={mode === m.id ? "chip skill-chip active" : "chip skill-chip"}
          onClick={() => onChange(m.id)}>
          {m.label}
        </button>
      ))}
    </div>
  );
}
