# DevFoundry Architecture

## Layers

### 1. Desktop shell — Tauri 2 + React 18 (`frontend/`)

- **Pages:** Forge, Research, History, Models, Plugins, Gateway, Services, Settings. Command palette (⌘K).
- **Native Rust commands** (`src-tauri/src/main.rs`):
  - Orchestrator lifecycle: `start_backend`, `stop_backend` — the app **spawns the FastAPI
    orchestrator on launch** (from `backend/.venv` or system Python), passing `.env`, and kills it on close.
  - Docker: `docker_available`, `docker_running`, `start_docker_desktop`, `start/stop_stack`,
    `stack_status`, `service_logs`.
  - System: `system_specs` (RAM/cores/chip/Metal), `open_url_window` (native child window — used for
    the FreeLLMAPI dashboard, bypasses X-Frame-Options), `read_env`, `save_env`.
- Talks to the backend at `http://localhost:9100` (REST + WebSocket). CSP permits localhost + https so
  the Canvas can preview external assets and providers are reachable.

### 2. Orchestrator — FastAPI (`backend/`)

Default **embedded mode** (`DEVFOUNDRY_EMBEDDED=1`): every stage runs in-process — no sidecars.

- **Pipeline** (`app/orchestrator/embedded.py`): Spec → Design → Codebase → Tasks → Refine → Deploy.
  - Codegen uses a delimited `=== FILE: path ===` format with a reformat retry.
  - Design system + selected **skills** (`app/skills.py`) + **RAG context** (`app/knowledge.py`)
    are injected into the design and codegen prompts.
  - Refine runs tests **once** in CI mode; unrunnable envs are skipped, genuine failures iterate (≤3).
  - Deploy picks a provider (`app/orchestrator/deploy_providers.py`); zip fallback always works.
- **LLM client** (`app/llm.py`): candidate chain — stage expert → active model → rotation list →
  legacy keys → auto-detected local. Retryable errors rotate to the next candidate.
- **Provider catalog** (`app/llm_providers.py`): 24 providers, live model listing, configured/free flags.
- **EventBus** (`app/events/bus.py`): per-run pub/sub with history replay; also **persists every event**.
- **Store** (`app/store.py`): SQLite for runs + events (`workspace/devfoundry.db`); rehydrated on startup.
- **Knowledge** (`app/knowledge.py`): SQLite KB, Ollama embeddings + cosine (keyword fallback).
- **Research** (`app/research.py`): search chain (Brave/Tavily → SearXNG → Wikipedia) + r.jina.ai reader.
- Config (`app/config.py`) reads `.env` **live** so saved keys/settings apply without a restart.

Optional **isolated mode**: the five framework sidecars (`services/*`) run in Docker with SearXNG and
Qdrant. Same event contract to the UI.

### 3. API surface (`backend/app/api/`)

| Area | Endpoints |
|---|---|
| Runs | `POST /runs`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/events`, `POST /runs/{id}/stop`, `POST /runs/{id}/redeploy`, `DELETE /runs/{id}`, `ws /ws/runs/{id}` |
| Project files | `GET/PUT/DELETE /runs/{id}/file`, `GET /runs/{id}/files`, `GET /runs/{id}/download`, `POST /runs/{id}/upload` |
| LLM | `GET /llm/providers`, `GET /llm/providers/{id}/models`, `GET /llm/routing`, `POST /llm/test` |
| Hardware/router | `POST /hardware/recommend`, `GET /router/providers`, `GET /skills`, `GET/POST /knowledge` |
| MCP | `GET/POST /mcp/servers`, `DELETE /mcp/servers/{name}`, `GET /mcp/servers/{name}/tools`, `POST /mcp/servers/{name}/call` |
| Research/extra | `ws /research/ws`, `GET /gateway/status`, `GET/POST/DELETE /presets` |
| Deploy | `GET /deploy/providers` |

## Data flow (one run)

```
idea + skills ──POST /runs──▶ orchestrator
  spec:    LLM ──▶ PRD, architecture, API spec
  design:  LLM ──▶ design brief (skills + design system)
  codegen: LLM (design brief + skills + RAG knowledge) ──▶ files ──▶ workspace/<run>/app
  tasks:   LLM ──▶ [tasks]
  refine:  per task: LLM edits; then npm install + test (CI mode, ≤3 fix iterations on real failure)
  deploy:  provider (netlify/vercel/cloudflare/surge/hf/docker/zip)
every step ──▶ EventBus ──▶ WebSocket ──▶ UI, and ──▶ SQLite (history)
```

## Security posture

- Credentials live in `.env`, written only by the Settings page via a native command; read live;
  never bundled or sent anywhere except the provider APIs the pipeline calls.
- Generated files are materialized with a path-traversal guard; project code runs only inside the user's
  own toolchain (npm/pytest) or containers, never elevated.
- CSP pins the webview; MCP servers run as user-level subprocesses with only the env they're given.
- Ad-hoc signed for local use; distribution needs Developer ID + notarization (see ROADMAP).
