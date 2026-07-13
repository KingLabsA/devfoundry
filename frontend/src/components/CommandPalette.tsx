import { useEffect, useMemo, useState } from "react";
import { Page } from "./Sidebar";
import { THEMES, applyTheme } from "../themes";

interface Command { label: string; hint: string; run: () => void }

export function CommandPalette({ onNavigate }: { onNavigate: (p: Page) => void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        setQuery("");
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const commands: Command[] = useMemo(() => {
    const pages: [Page, string][] = [
      ["forge", "Forge"], ["research", "Deep Research"], ["runs", "Build History"],
      ["models", "Models"], ["plugins", "Plugins"], ["gateway", "Gateway"],
      ["services", "Services"], ["settings", "Settings"],
    ];
    const nav: Command[] = pages.map(([id, label]) => ({
      label: `Go to ${label}`, hint: "navigation", run: () => { onNavigate(id); setOpen(false); },
    }));
    const themes: Command[] = THEMES.map((t) => ({
      label: `Theme: ${t.label}`, hint: "appearance", run: () => { applyTheme(t.id); setOpen(false); },
    }));
    return [...nav, ...themes];
  }, [onNavigate]);

  if (!open) return null;
  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="palette-overlay" onClick={() => setOpen(false)}>
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <input autoFocus className="palette-input" placeholder="Type a command… (⌘K)"
          value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && filtered[0]) filtered[0].run(); }} />
        <div className="palette-list">
          {filtered.length === 0 && <div className="palette-empty">No commands</div>}
          {filtered.slice(0, 12).map((c, i) => (
            <button key={i} className="palette-item" onClick={c.run}>
              <span>{c.label}</span><span className="palette-hint">{c.hint}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
