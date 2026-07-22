# DevFoundry — Troubleshooting

## Startup

| Symptom | Cause & fix |
|---|---|
| Header dots stay red; no backend | The app spawns the orchestrator on launch. If it didn't, check `/tmp/devfoundry-autostart.log` and `orchestrator.log` in the project dir. Usually a rapid relaunch race — quit fully and reopen, or click **Start services** in the header. |
| "Python not found" in autostart log | The app runs `backend/.venv/bin/uvicorn` if present, else system `python3 -m uvicorn`. Install Python 3.11+ or create the venv: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. |
| Backend up but pages say "offline" | Give it a few seconds — the first import loads several libraries. Then **Refresh**. |

## Models & LLM

| Symptom | Fix |
|---|---|
| "No LLM provider configured" | Open **Models** → paste a key and click **Use**, or run a local runtime (Ollama/LM Studio/FreeLLMAPI). It auto-detects local ones. Confirm with **⚡ Test LLM**. |
| Provider "models" button errors 401 | Wrong/expired key. The error distinguishes auth failure from unreachable. Re-paste the key (Models page) — it applies live. |
| FreeLLMAPI 401 | It requires its key even to list models. Paste `FREELLMAPI_KEY` in Settings → Providers. Use model **`auto`** (its own catalog names, not OpenAI names). |
| Codegen fails to parse | Weak models sometimes mangle output. Switch to a stronger/coder model on Models; codegen already retries with a stricter format. |
| Slow runs | The active model is slow (e.g. a large local model). Pick a faster one, or set MoE stage experts so codegen uses your best coder model and planning uses a fast one. |

## Test suite (refine stage)

| Symptom | Cause & fix |
|---|---|
| "Tests skipped — not a code failure" | Correct behavior: the generated test env can't run (missing dep, watch-mode runner, no jsdom). DevFoundry runs tests once (CI mode) and skips unrunnable ones instead of looping. |
| Old runs showed endless "Fix failing tests 1/2/3" | Fixed: `vitest` defaulted to watch mode so `npm test` never exited. Now forced to one-shot (`CI=true` + `--run`). Re-run to see the clean behavior. |
| Want tests to actually pass | The design system now generates a runnable setup (`vitest run`, jsdom, setupTests). Use a strong model for best adherence. |

## Deployment

| Symptom | Fix |
|---|---|
| "Container build failed — packaging zip" | Expected for static/JS apps with no Dockerfile. `auto` only tries Docker when a Dockerfile exists; otherwise it makes a zip. |
| Cloud deploy fails | Missing token → it falls back to a zip and tells you which token to add (Settings → Deployment). Add it and **Re-deploy**. |
| Superpowers/docker deploy can't reach daemon | Only relevant in isolated mode; the compose mounts the Docker socket. Ensure Docker Desktop is running. |

## Plugins (MCP)

| Symptom | Fix |
|---|---|
| A server shows **error** / 0 tools | TypeScript servers use `npx`; Python servers (fetch, git, time, sqlite) use `uvx` — install uv (`brew install uv`). Key-needing servers (🔑) need their token in `.env`. |
| Stale server with wrong command | The catalog shows **⟳ repair** when an install drifts from the current catalog — click it to overwrite with the correct command. |
| github/brave/slack servers won't connect | They need a key. Add it in Settings, then re-install from the catalog (it reads the key from `.env`). |

## Deep Research

| Symptom | Fix |
|---|---|
| Few or off-topic results | The keyless fallback is Wikipedia (broad). Add a free **Brave** or **Tavily** key (Settings → Research) for real web search, or start the bundled SearXNG (Services → Start All). |
| "connection failed" | Backend or the research WS isn't reachable. Ensure the app backend is up (header dots green). |

## Gateway

| Symptom | Fix |
|---|---|
| Shows "offline" | Click **▶ Start gateway**. If embedded (default), it starts natively — no Docker. Legacy Docker setups: it starts the container, launching Docker Desktop first if needed. The banner tells you exactly what's wrong, and the backend auto-starts the gateway at boot. |
| "not embedded yet" | Click **⬇ Embed gateway** (Gateway or Services page) — one-time clone + build into the workspace (needs Node.js ≥ 20, which the pipeline already uses). Existing Docker-gateway data (provider keys) is migrated automatically. |
| Embedded gateway won't start | See `workspace/freellmapi-native.log`. |
| Dashboard won't embed | By design — FreeLLMAPI sends `X-Frame-Options: SAMEORIGIN`. Use **Open dashboard in app window** (native child window) or **Open in browser**. |
| Shows "offline" but container runs | The status is checked by the backend (which can reach it). If it still shows offline, the container isn't on `:3002` — set `FREELLMAPI_URL`. |

## Data & reset

- Runs/events: `workspace/devfoundry.db` · Knowledge: `workspace/knowledge.db` · Presets:
  `workspace/presets.json` · MCP servers: `mcp.json` · Config: `.env`.
- To reset history, delete `workspace/devfoundry.db` (or delete runs from the History page).

## Getting logs

- Autostart: `/tmp/devfoundry-autostart.log`
- Orchestrator: `orchestrator.log` (project root)
- Isolated-mode services: **Services** page → **logs** per service.
