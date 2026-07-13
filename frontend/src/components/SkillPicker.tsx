import { useEffect, useState } from "react";
import { BASE } from "../api/client";

interface Skill { id: string; label: string; desc: string }

/** Select design/capability skills that shape the pipeline toward premium output. */
export function SkillPicker({ selected, onChange }: {
  selected: string[];
  onChange: (s: string[]) => void;
}) {
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    fetch(`${BASE}/api/skills`).then((r) => r.json()).then(setSkills).catch(() => {});
  }, []);

  if (skills.length === 0) return null;
  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);

  return (
    <div className="skill-picker">
      <span className="skill-label">✨ Skills</span>
      {skills.map((s) => (
        <button key={s.id} title={s.desc}
          className={selected.includes(s.id) ? "chip skill-chip active" : "chip skill-chip"}
          onClick={() => toggle(s.id)}>
          {s.label}
        </button>
      ))}
    </div>
  );
}
