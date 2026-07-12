import { useState } from "react";

const EXAMPLES = [
  "Build a Slack bot for OKR tracking",
  "Build a recipe box app with meal planning",
  "Build a markdown notes app with tags and search",
];

export function IdeaInput({ disabled, onSubmit }: { disabled: boolean; onSubmit: (idea: string) => void }) {
  const [idea, setIdea] = useState("");
  const valid = idea.trim().length >= 10;

  const submit = () => {
    if (valid && !disabled) onSubmit(idea.trim());
  };

  return (
    <section className="idea-section">
      <form
        className="idea-input"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit();
          }}
          placeholder='Describe your app idea… (⌘↵ to forge)'
          rows={3}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !valid}>
          {disabled ? "Building…" : "Forge It"}
        </button>
      </form>
      {!disabled && (
        <div className="examples">
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" className="chip" onClick={() => setIdea(ex)}>
              {ex}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
