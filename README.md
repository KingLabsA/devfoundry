# DevFoundry

Autonomous software development factory. Give it an app idea in natural
language; it produces specs, code, tasks, refinements, and a deployed app.

## Pipeline

| Stage  | Tool        | Output                                      |
|--------|-------------|---------------------------------------------|
| Spec   | MetaGPT     | PRD, architecture, API specs                |
| Code   | Bolt.diy    | Full application codebase                   |
| Tasks  | Orc         | Task breakdown + AI-dev assignment          |
| Refine | OpenCode    | Implemented tasks, bug fixes, passing tests |
| Deploy | Superpowers | Packaged container + running app            |

Progress streams live to the Tauri UI over WebSocket (`/ws/runs/{run_id}`).

## Quick start

```bash
cp .env.example .env   # fill in OPENAI_API_KEY / ANTHROPIC_API_KEY
docker compose up -d   # backend (:9100) + 5 isolated framework services (:9101-:9105)
cd frontend && npm install && npm run tauri dev
```

## Architecture

- `frontend/` — Tauri 2 + React 18 desktop app (idea input, pipeline timeline, live logs)
- `backend/` — FastAPI orchestrator (REST + WebSocket, per-run event bus)
- `services/` — one Docker sidecar per framework, each exposing a thin HTTP adapter with `/health`

All credentials come from environment variables; nothing is hardcoded.

## Tests

```bash
cd backend && python -m pytest
```
