# Roadmap & Honest Gap Analysis

Expert assessment of where DevFoundry stands today, what's blocking a public
launch, and the order to fix it. Severity: 🔴 launch-blocking · 🟡 important · 🟢 polish.

## What genuinely works today

- Native desktop app: sidebar shell, Forge pipeline UI, live WebSocket streaming
  with replay, Runs history, Services page with integrated Docker lifecycle
  (including auto-launching Docker Desktop), Settings persisted to `.env`.
- Orchestrator: staged pipeline, event bus, health fan-out, bounded refine loop,
  path-traversal guard, demo mode, test suite.
- MetaGPT and OpenCode adapters call real upstream entrypoints.
- Orc adapter: real Claude-backed task decomposition.
- Superpowers adapter: real `docker build` + `docker run` packaging.

## Gaps

### 🔴 1. Bolt.diy adapter calls an API that doesn't exist upstream
`services/boltdiy/adapter.mjs` imports `build/headless.js`, which bolt.diy does not
ship. **Fix:** replace with a direct codegen service — prompt an LLM (via the
configured provider) to emit a file map from the MetaGPT specs. ~1 day. This is the
single biggest correctness gap.

### 🔴 2. Superpowers container needs the Docker socket
`docker` inside the superpowers container can't reach the host daemon without
mounting `/var/run/docker.sock` (compose change) — or run deploys on the host via
a native command. Decide and wire it. ~2 hours.

### 🔴 3. No signed/notarized build
Ad-hoc signature means Gatekeeper warnings for anyone who downloads the dmg.
Needs an Apple Developer ID, `tauri-plugin-updater` config, and notarization in CI. ~1 day.

### 🟡 4. Run persistence
Runs live in orchestrator memory; restart loses history. Add SQLite (one table:
runs + serialized events). ~half day.

### 🟡 5. Provider keys in plaintext `.env`
Works, standard for dev tools, but the desktop-app bar is higher: move to the macOS
Keychain (`tauri-plugin-stronghold` or `security` CLI) with `.env` as fallback. ~1 day.

### 🟡 6. LLM provider routing is uneven
Settings collects five provider keys + a custom gateway, but only Orc reads
`ANTHROPIC_API_KEY` explicitly; MetaGPT wants OpenAI-style config. Introduce one
`LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY` contract consumed by every sidecar. ~1 day.

### 🟡 7. Static service logs
Logs page shows a 200-line snapshot. Stream `docker compose logs -f` through a
Tauri event channel. ~half day.

### 🟡 8. Cancel/retry controls
A running pipeline can't be cancelled from the UI and a failed stage can't be
retried without starting over. Orchestrator already holds the asyncio tasks —
add `DELETE /api/runs/{id}` + a per-stage retry. ~1 day.

### 🟢 9. Windows/Linux builds, auto-update, crash reporting, onboarding
first-run wizard, generated-project browser ("open in Finder / editor"), template
gallery, richer artifact rendering (markdown preview for PRDs).

## Suggested order to launch

1. Fix Bolt.diy adapter (🔴1) and Docker socket (🔴2) → the pipeline is honest end-to-end.
2. Unify LLM provider contract (🟡6) → any provider actually works.
3. SQLite persistence (🟡4) + cancel/retry (🟡8) → feels like a product, not a demo.
4. Sign + notarize (🔴3) → distributable.
5. Everything else post-launch, driven by user feedback.

Total to a credible v0.2 public beta: **roughly one focused week**.
