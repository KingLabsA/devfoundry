# Contributing to DevFoundry

Thanks for your interest! DevFoundry is a Tauri (React) desktop app with a FastAPI orchestrator.

## Setup

```bash
git clone <repo-url> devfoundry && cd devfoundry
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# frontend
cd ../frontend && npm install
```

## Run in dev

```bash
# terminal 1 — backend (embedded mode, hot reload)
cd backend && DEVFOUNDRY_MOCK=1 .venv/bin/uvicorn app.main:app --port 9100 --reload
# terminal 2 — desktop app (hot reload)
cd frontend && npm run tauri dev
```

`DEVFOUNDRY_MOCK=1` gives a fast, deterministic scripted pipeline — ideal for UI work without spending tokens.

## Checks before a PR

```bash
cd backend && .venv/bin/python -m pytest -q      # backend tests
cd frontend && npx tsc --noEmit                  # frontend typecheck
cd frontend && npm run tauri build               # full native build (slower)
```

## Project layout

- `frontend/src/` — React UI (pages/, components/, api/, hooks/, themes.ts)
- `frontend/src-tauri/src/main.rs` — native commands (orchestrator lifecycle, Docker, system, windows)
- `backend/app/` — FastAPI: `orchestrator/` (pipeline), `api/` (routes), `llm*.py`, `skills.py`,
  `knowledge.py`, `research.py`, `store.py`
- `services/` — Docker sidecars (isolated mode) + SearXNG config
- `docs/`, `website/` — documentation and landing page

## Guidelines

- Match the surrounding style; keep changes focused.
- Add a skill in `backend/app/skills.py`, a knowledge entry in `knowledge.py` SEED, or an MCP server in
  the `CATALOG` in `frontend/src/pages/PluginsPage.tsx` — these are the easy, high-value contributions.
- Verify real behavior (run a pipeline), not just types.
- Don't hardcode secrets; everything goes through `.env` / the Settings page.

## Commit / PR

- Clear, imperative commit messages describing the change and why.
- Note what you verified (tests, a real run) in the PR description.
