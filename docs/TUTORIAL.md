# DevFoundry Tutorial

Three paths, in increasing order of setup: **demo mode** (60 seconds, nothing needed),
**full pipeline** (Docker + one API key), and **development mode** (hacking on DevFoundry itself).

---

## Path 1 — Demo mode (no Docker, no API keys)

Perfect for a first look, screenshots, or a live demo.

1. Start the orchestrator locally with the mock pipeline enabled:

   ```bash
   cd devfoundry/backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   DEVFOUNDRY_MOCK=1 .venv/bin/uvicorn app.main:app --port 9100
   ```

2. Open **DevFoundry.app**. The header dots turn green (backend up).
3. On **Forge**, click an example chip — say *"Build a Slack bot for OKR tracking"* — and hit **Forge It**.
4. Watch the run: the timeline advances Specs → Codebase → Tasks → Refinement → Deploy,
   the **Live Log** streams each step, and the **Artifacts** tab collects a PRD,
   architecture doc, codebase manifest, task board, diffs, and a deployment record.
5. Check the **Runs** page — your run is in the history with stage `done`.

Everything you saw is exactly what a real run looks like; demo mode just scripts the content.

---

## Path 2 — Full pipeline

### One-time setup

1. Install **Docker Desktop** (docker.com) — you don't need to start it; DevFoundry will.
2. Open DevFoundry → **Settings**:
   - Paste an **Anthropic** key (used by the Orc task planner) and any other providers you use.
   - Optionally point **Custom gateway** at a self-hosted OpenAI-compatible proxy.
   - Click **Save** — this writes the project `.env`; keys live only on your disk.
3. Click **▶ Start services** in the header. DevFoundry will:
   - launch Docker Desktop if the daemon is down and wait for it,
   - run `docker compose up -d` for the six services,
   - build the five framework images on first run (**several minutes** — watch
     progress with the **logs** buttons on the Services page).

### Every run after that

1. **Forge** → describe your idea → **Forge It** (`⌘↵`).
2. The five stages run in order; artifacts stream in as they're produced.
3. Generated projects land in `workspace/<run_id>/` inside the project directory.
4. The deploy stage builds and starts a container for your app; its port mapping
   appears in the deployment artifact.

### If something fails

- The failing stage's card turns red and the status pill shows **Failed**.
- Services page → **logs** for the responsible service is the first place to look.
- Fix (usually a missing key or a service that needs a restart), then forge again —
  each run is independent.

---

## Path 3 — Developing DevFoundry

```bash
# backend with hot reload
cd backend && .venv/bin/uvicorn app.main:app --port 9100 --reload

# desktop app with hot reload (opens its own window)
cd frontend && npm run tauri dev

# tests
cd backend && .venv/bin/python -m pytest
cd frontend && npx tsc --noEmit
```

Set `DEVFOUNDRY_MOCK=1` on the backend while working on UI — you get instant,
deterministic pipeline runs without burning tokens.

---

## Recording a demo video

1. Backend in demo mode (Path 1).
2. Resize the window to 1280×800 for a crisp recording.
3. Script: type idea → Forge It → let the timeline complete (~45 s) → open
   Artifacts → click the PRD → switch to Runs page. That's the whole story arc.
