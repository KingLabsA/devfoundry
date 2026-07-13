export interface Theme {
  id: string;
  label: string;
  vars: Record<string, string>;
}

export const THEMES: Theme[] = [
  {
    id: "midnight", label: "Midnight (default)",
    vars: { "--bg": "#0c0f14", "--panel": "#141922", "--panel-2": "#1a2030", "--border": "#262e3f",
      "--text": "#e8edf5", "--muted": "#8b96a8", "--accent": "#f0883e", "--accent-soft": "rgba(240,136,62,0.14)",
      "--ok": "#3fb950", "--fail": "#f85149" },
  },
  {
    id: "ocean", label: "Ocean",
    vars: { "--bg": "#0a0f1c", "--panel": "#111a2e", "--panel-2": "#17233d", "--border": "#233152",
      "--text": "#e6eefc", "--muted": "#8296b8", "--accent": "#3b9dff", "--accent-soft": "rgba(59,157,255,0.16)",
      "--ok": "#3fb950", "--fail": "#f85149" },
  },
  {
    id: "forest", label: "Forest",
    vars: { "--bg": "#0b120e", "--panel": "#111d16", "--panel-2": "#17281e", "--border": "#243b2d",
      "--text": "#e7f3ea", "--muted": "#87a693", "--accent": "#37c76a", "--accent-soft": "rgba(55,199,106,0.15)",
      "--ok": "#3fb950", "--fail": "#f85149" },
  },
  {
    id: "grape", label: "Grape",
    vars: { "--bg": "#0f0b16", "--panel": "#181022", "--panel-2": "#221630", "--border": "#342247",
      "--text": "#efe8f7", "--muted": "#9a8bb0", "--accent": "#b06bff", "--accent-soft": "rgba(176,107,255,0.16)",
      "--ok": "#3fb950", "--fail": "#f85149" },
  },
  {
    id: "nord", label: "Nord",
    vars: { "--bg": "#2e3440", "--panel": "#3b4252", "--panel-2": "#434c5e", "--border": "#4c566a",
      "--text": "#eceff4", "--muted": "#9aa5b8", "--accent": "#88c0d0", "--accent-soft": "rgba(136,192,208,0.18)",
      "--ok": "#a3be8c", "--fail": "#bf616a" },
  },
  {
    id: "paper", label: "Paper (light)",
    vars: { "--bg": "#f5f3ee", "--panel": "#ffffff", "--panel-2": "#efece5", "--border": "#dcd7cc",
      "--text": "#25211a", "--muted": "#6b6558", "--accent": "#d1730a", "--accent-soft": "rgba(209,115,10,0.12)",
      "--ok": "#2f8f46", "--fail": "#c8422f" },
  },
];

const KEY = "devfoundry.theme";

export function applyTheme(id: string) {
  const theme = THEMES.find((t) => t.id === id) ?? THEMES[0];
  const root = document.documentElement;
  for (const [k, v] of Object.entries(theme.vars)) root.style.setProperty(k, v);
  localStorage.setItem(KEY, theme.id);
}

export function currentTheme(): string {
  return localStorage.getItem(KEY) ?? THEMES[0].id;
}
