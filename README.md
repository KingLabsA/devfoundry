# ⬢ DevFoundry

**Type an app idea. Get specs, code, tests, and a deployed app — while you watch.**

DevFoundry is a native desktop app (macOS, Tauri) that runs an autonomous software
factory on your own machine. It chains five AI development stages into one pipeline
and streams every document, diff, test result, and deploy log live into the UI.

| Stage  | Engine      | Output                                      |
|--------|-------------|---------------------------------------------|
| Spec   | MetaGPT     | PRD, architecture, API specs                |
| Code   | Bolt.diy    | Full application codebase                   |
| Tasks  | Orc         | Feature breakdown + AI-developer assignment |
| Refine | OpenCode    | Implemented tasks, bug fixes, passing tests |
| Deploy | Superpowers | Packaged container, running app             |

## Why DevFoundry

- **Local-first.** Your ideas, keys, and generated code never leave your machine.
- **Bring your own models.** Anthropic, OpenAI, OpenRouter, Groq, Google — or any
  OpenAI-compatible gateway (self-hosted proxies work).
- **Transparent.** Every stage streams its artifacts live; nothing is a black box.
- **Native.** Real desktop app (8 MB), integrated Docker control, no browser tabs.

## Install

Download `DevFoundry_x.y.z_aarch64.dmg` from Releases, drag to Applications.

Or build from source:

```bash
git clone <repo-url> devfoundry && cd devfoundry
cd frontend && npm install && npm run tauri build
# bundles land in frontend/src-tauri/target/release/bundle/
```

**Requirements:** macOS (Apple Silicon), Docker Desktop (for the full pipeline),
Node 20+, Rust (only if building from source).

## Quick start

1. Open DevFoundry → **Settings** → paste at least one LLM provider key → Save.
2. Click **▶ Start services** in the header. If Docker Desktop isn't running,
   DevFoundry launches it, waits for the daemon, and brings the stack up.
   The first start builds five Docker images — give it several minutes.
3. Go to **Forge**, type your idea (`⌘↵` to submit), and watch the timeline light up.

## Try it in 60 seconds (demo mode — no Docker, no keys)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
DEVFOUNDRY_MOCK=1 .venv/bin/uvicorn app.main:app --port 9100
```

Open the DevFoundry app, forge any idea, and a fully scripted pipeline run streams
through every stage — perfect for demos and screenshots. See
[docs/TUTORIAL.md](docs/TUTORIAL.md) for the full walkthrough.

## Architecture

```
┌────────────────────── DevFoundry.app (Tauri 2 + React) ──────────────────────┐
│  Forge · Runs · Services (Docker control) · Settings (providers, endpoints)  │
└──────────────┬────────────────────────────────────────────────┬──────────────┘
               │ REST + WebSocket (localhost:9100)              │ Rust commands
┌──────────────▼──────────────┐                    ┌────────────▼─────────────┐
│  FastAPI orchestrator       │                    │  docker compose up/down  │
│  pipeline + event bus       │                    │  .env read/write         │
└─┬──────┬──────┬──────┬──────┘                    └──────────────────────────┘
  ▼      ▼      ▼      ▼      ▼
MetaGPT Bolt.diy Orc OpenCode Superpowers      (isolated Docker sidecars :9101-:9105)
```

Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Cannot connect to the Docker daemon" | Docker Desktop isn't running. Click **Start services** — DevFoundry now launches it for you and waits. |
| Stack starts but health dots stay red | First build still in progress — check per-service **logs** on the Services page. |
| "ANTHROPIC_API_KEY not set" in Orc logs | Add the key in **Settings**, save, then Stop All → Start All. |
| Want to try the UI without any setup | Run the backend in demo mode (`DEVFOUNDRY_MOCK=1`, see above). |

## Project status & roadmap

Working today: the desktop app, orchestrator, live streaming, Docker lifecycle
management, settings, demo mode, and the MetaGPT/OpenCode adapters. The Bolt.diy
headless adapter and parts of the deploy flow are still maturing — the honest
gap-by-gap assessment lives in [docs/ROADMAP.md](docs/ROADMAP.md).

## Docs

- [Tutorial — first run, demo mode, real pipeline](docs/TUTORIAL.md)
- [Architecture deep-dive](docs/ARCHITECTURE.md)
- [Roadmap & gap analysis](docs/ROADMAP.md)
- [Launch checklist](docs/LAUNCH.md)

## License

MIT — see [LICENSE](LICENSE).
