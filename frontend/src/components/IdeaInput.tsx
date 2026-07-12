import { useState } from "react";

export function IdeaInput({ disabled, onSubmit }: { disabled: boolean; onSubmit: (idea: string) => void }) {
  const [idea, setIdea] = useState("");
  return (
    <form
      className="idea-input"
      onSubmit={(e) => {
        e.preventDefault();
        if (idea.trim().length >= 10) onSubmit(idea.trim());
      }}
    >
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        placeholder='Describe your app idea, e.g. "Build a Slack bot for OKR tracking"'
        rows={3}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || idea.trim().length < 10}>
        {disabled ? "Building..." : "Forge It"}
      </button>
    </form>
  );
}
