import { useState } from "react";

interface Template { label: string; cat: string; idea: string }
const TEMPLATES: Template[] = [
  { label: "Slack OKR bot", cat: "Automation", idea: "Build a Slack bot for OKR tracking with weekly check-in reminders and a progress dashboard" },
  { label: "Markdown notes", cat: "Productivity", idea: "Build a markdown notes app with tags, full-text search, and local persistence" },
  { label: "Recipe box", cat: "Lifestyle", idea: "Build a recipe box app with meal planning, a shopping-list generator, and categories" },
  { label: "Kanban board", cat: "Productivity", idea: "Build a Kanban board app with drag-and-drop cards, columns, and labels" },
  { label: "URL shortener", cat: "Web", idea: "Build a URL shortener with click analytics and a QR code generator" },
  { label: "AI chat UI", cat: "AI", idea: "Build a streaming AI chat interface with conversation history and model selection" },
  { label: "Expense tracker", cat: "Finance", idea: "Build an expense tracker with categories, monthly budgets, and charts" },
  { label: "Blog + CMS", cat: "Web", idea: "Build a blog with a markdown CMS, tags, and an RSS feed" },
  { label: "Habit tracker", cat: "Lifestyle", idea: "Build a habit tracker with streaks, daily reminders, and a heatmap calendar" },
  { label: "REST API + docs", cat: "Backend", idea: "Build a REST API for a todo service with OpenAPI docs and JWT auth" },
  { label: "Portfolio site", cat: "Web", idea: "Build a personal portfolio site with a projects grid, about section, and contact form" },
  { label: "Weather dashboard", cat: "Web", idea: "Build a weather dashboard with a 5-day forecast, search by city, and unit toggle" },
];

export function IdeaInput({
  disabled, onSubmit, running, onStop,
}: {
  disabled: boolean;
  onSubmit: (idea: string) => void;
  running?: boolean;
  onStop?: () => void;
}) {
  const [idea, setIdea] = useState("");
  const [showAll, setShowAll] = useState(false);
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
          autoFocus
        />
        {running ? (
          <button type="button" className="stop-btn-lg" onClick={onStop}>■ Stop</button>
        ) : (
          <button type="submit" disabled={disabled || !valid}>Forge It</button>
        )}
      </form>
      {!disabled && (
        <>
          <div className="examples">
            {(showAll ? TEMPLATES : TEMPLATES.slice(0, 6)).map((t) => (
              <button key={t.label} type="button" className="chip" title={t.idea} onClick={() => setIdea(t.idea)}>
                {t.label} <span className="chip-cat">{t.cat}</span>
              </button>
            ))}
            <button type="button" className="chip" onClick={() => setShowAll((s) => !s)}>
              {showAll ? "less ▲" : `+${TEMPLATES.length - 6} templates ▾`}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
