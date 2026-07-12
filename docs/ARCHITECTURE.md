# DevFoundry Architecture

## Layers

### 1. Desktop shell — Tauri 2 + React 18 (`frontend/`)

- **Pages:** Forge (pipeline UI), Runs (history), Services (Docker lifecycle), Settings (providers/endpoints).
- **Native Rust commands** (`src-tauri/src/main.rs`): `docker_available`, `docker_running`,
  `start_docker_desktop`, `start_stack`, `stop_stack`, `stack_status`, `service_logs`,
  `read_env`, `save_env`. The webview never shells out directly; all system access
  goes through these audited commands.
- **Startup flow** (`ensureStackUp` in `src/api/native.ts`): check Docker installed →
  launch Docker Desktop if daemon down → poll `docker info` up to 2 min → `compose up -d`.
- Talks to the orchestrator over `http://localhost:9100` (REST) and
  `ws://localhost:9100/ws/runs/{id}` (event stream). CSP restricts connections to
  exactly that origin.

### 2. Orchestrator — FastAPI (`backend/`)

- `POST /api/runs` starts a pipeline as an asyncio task; `GET /api/runs` lists history;
  `GET /api/health` fans out to every sidecar's `/health`.
- **EventBus** (`app/events/bus.py`): per-run pub/sub with full history replay, so a
  WebSocket client that connects late still sees every event from the start.
- **Pipeline** (`app/orchestrator/pipeline.py`): five sequential stages with a bounded
  refine loop (up to 3 test-fix iterations). All failures land in the event stream —
  the UI never has to poll for errors.
- **Mock pipeline** (`app/orchestrator/mock.py`, `DEVFOUNDRY_MOCK=1`): scripted run
  used for demos and UI development.
- Path-traversal guard when materializing generated files to the workspace.

### 3. Framework sidecars (`services/`, one container each)

| Service | Port | Adapter | Notes |
|---|---|---|---|
| metagpt | 9101 | FastAPI wrapper around `metagpt.software_company.generate_repo` | produces PRD / architecture / API spec |
| boltdiy | 9102 | Express wrapper (headless API) | ⚠ upstream has no stable headless entrypoint yet — see ROADMAP |
| opencode | 9103 | Express wrapper around the `opencode` CLI | runs instructions + test cycles inside the generated repo |
| orc | 9104 | FastAPI task planner (Claude-backed decomposition + assignment) | in-memory task board |
| superpowers | 9105 | FastAPI deployer (docker build + run) | needs the host Docker socket in production use |

Isolation rationale: each framework has heavy, conflicting dependency trees; containers
keep them independent, restartable, and individually observable.

## Data flow for one run

```
idea ──POST /api/runs──▶ orchestrator
  spec:    orchestrator ──▶ metagpt   ──▶ {prd, architecture, api_spec}
  codegen: orchestrator ──▶ boltdiy   ──▶ {files} ──materialize──▶ workspace/<run>/app
  tasks:   orchestrator ──▶ orc       ──▶ [{task, assignee}]
  refine:  orchestrator ──▶ opencode  ──▶ diffs; test loop (≤3 iterations)
  deploy:  orchestrator ──▶ superpowers ─▶ {image, container, url}
every step ──▶ EventBus ──▶ WebSocket ──▶ UI (log lines, artifacts, stage status)
```

## Security posture

- All credentials in `.env`, written only by the Settings page via a native command;
  never bundled, never sent anywhere except the provider APIs the sidecars call.
- Tauri CSP pins network access to `localhost:9100`.
- Generated code is materialized with a path-traversal check and executed only
  inside containers, never on the host.
- The app is ad-hoc signed for local use; distribution requires Developer ID +
  notarization (see LAUNCH.md).
