# Changelog

All notable changes to DevFoundry. Format loosely follows Keep a Changelog.

## [0.2.6]

### Added
- **Managed FreeLLMAPI gateway — no more terminal.** The gateway is a Docker service, and
  until now the app only *consumed* it: if the container (or Docker itself) was stopped, the
  Gateway page just said "offline" and left you to fix it by hand. Now the app owns the
  lifecycle: `GET/POST /api/embedded/freellmapi/{status,start,stop}` detect the container or
  compose project (`FREELLMAPI_DIR` overrides; `~/freellmapi` auto-detected), a **▶ Start
  gateway** button on the Gateway page handles the full path — launching Docker Desktop if
  needed, then the container, then waiting for the port — and the backend **auto-restarts the
  gateway container at boot** whenever Docker is already running. The offline banner now says
  exactly what's wrong (no Docker CLI / daemon stopped / container stopped / no install found)
  instead of a generic message.

## [0.2.5]

### Fixed
- **Plugins (and npm/docker tooling) now work when the app is launched from Finder/Dock.**
  GUI launches get a minimal PATH without Homebrew/npx/uvx, so every stdio MCP server failed
  with "No such file or directory" — and npm builds/deploy CLIs would have failed the same way.
  The orchestrator and all native spawns (backend, dev server, docker) now augment PATH with
  the standard tool locations. Reproduced under a Finder-identical environment: all plugins
  errored before the fix, all connect after.

## [0.2.4]

### Added
- **Sandbox for generated code** — LLM-generated code no longer runs with full user
  privileges. npm install/build/test and pytest execute under an OS sandbox
  (macOS `sandbox-exec`, Linux `bwrap`): file WRITES confined to the project directory
  + toolchain caches; reads/network allowed so builds work. `SANDBOX=0` opts out;
  `GET /api/sandbox/status` reports the active backend.
  VERIFIED: outside-project writes blocked, in-project writes + real `npm test` pass inside.
- **Install-fix loop** — a failed `npm install` (e.g. hallucinated package versions) is now a
  fixable error: the exact npm error is fed back to the model (fix package.json) and install
  retried (≤3). VERIFIED on a real failing project: install went red → fixed → green.
- **Real screen-recorded demo** (`screen-demo.mp4`, 73s): typing the idea, forging, the live
  pipeline, the finished run, and Build History — now the landing-page hero video.

### Fixed
- Skills row / Deploy dropdown could vanish forever if their first fetch raced the backend
  boot — now retried until the backend is up.
- Legacy provider fallbacks no longer inherit the active provider's model name
  (e.g. FreeLLMAPI's `auto` sent to Anthropic); each fallback uses its own default.
- Idea box autofocuses on the Forge page.
- Website “Get started” had a placeholder `<repo-url>`; now real install paths for all three
  surfaces (desktop / source / CLI+web).

## [0.2.3]

### Added
- **Embedded native services — Docker now fully optional on the desktop.** DevFoundry downloads
  the official Qdrant binary for your OS/arch (~69MB, one time) and supervises it as a native
  child process (auto-starts with the app once installed). Services page gains an
  "Embedded services — built in, no Docker" section with install/start/stop.
  Verified end-to-end with the Docker daemon down: install → run → RAG indexes and retrieves
  through the native instance.
- **Demo video assets** rendered from a real verified run's unedited event log:
  `demo.mp4` (1280×800, embedded on the landing page) + `demo-vertical.mp4` (1080×1920 for
  Reels/TikTok/Shorts).
- **Website live** at https://kinglabsa.github.io/devfoundry/ (landing + real docs page),
  published via GitHub Pages.

## [0.2.2]

### Added
- **CLI surface** — `pip install -e backend` → `devfoundry` command: `serve` (orchestrator +
  web app), `forge "idea" --skill --reasoning --deploy` (streams the pipeline), `research`
  (cited report, `--out file.md`), `runs`, `version`.
- **Web-app surface** — the orchestrator serves the full UI at `http://localhost:9100/app`
  (Claude Code-style multi-surface: desktop, CLI, web).
- **Website docs** — real documentation page (`website/docs.html`): get started, surfaces,
  models & reasoning, deploys, Docker-optional explainer, troubleshooting. Landing-page doc
  links now point at real pages (were dead relative .md links).
- Rich in-app About with author identity and acknowledgments; CREDITS.md.

### Changed
- **Attribution corrected everywhere**: created by **King3Djbl** of **KingLabs**
  (GitHub KingLabsA · HF King3Djbl · Ollama FableForge-AI) — in-app About, native bundle
  copyright/publisher (macOS About panel, deb/rpm/msi metadata), LICENSE, README, website.
  Installers from this release on carry the correct name.
- "No Docker required" made explicit across the website and docs — embedded mode is the
  default; Docker remains an optional extra for isolated mode and container deploys.

## [0.2.1]

### Added
- **Reasoning modes** (Forge page picker + `REASONING_MODE`/`REASONING_N`): user-selectable
  inference strategies — `fast` (single-shot), `balanced` (**ToT** on the design stage:
  expand K briefs → judge → prune), `deep` (balanced + **Self-MoA** codegen: N samples from
  the active model, judge ranks), `ensemble` (balanced + **MoA** codegen: proposals from
  distinct configured providers, judge ranks), and `auto` (entropy-inspired complexity probe
  routes among them). Verified live: deep mode ran ToT + Self-MoA with judge selection.
- `complete(override=(provider, model))` to force a specific provider for ensemble proposals.
- Dynamic version display (reads the app version at runtime — no stale strings).

### Fixed
- **Per-user default project directory** — installers no longer contain a hardcoded
  `/Users/<name>/…` path. The default is now computed at runtime from `$HOME`
  (`~/Documents/devfoundry`), exposed via a `get_default_project_dir` command and seeded
  into the frontend on first launch. v0.2.0 installers pointed at the developer's home
  directory, which broke orchestrator autostart on any other machine (and leaked a
  username in the public source).
- ToT design-candidate failures are now surfaced in the event log instead of silently
  swallowed before fallback.

## [0.2.0] — first public release

### Added
- **Embedded mode** (default): the whole pipeline runs in-process; the app auto-starts the
  orchestrator on launch. No Docker required.
- **24 LLM providers** with live model fetch, per-provider keys (read live), zero-config auto-detect
  of local runtimes, keyless **OpenCode Zen**, and **FreeLLMAPI**.
- **MoE stage experts**, **rotation/failover**, and a one-click **auto-router** across free providers.
- **Hardware detection** → best local-LLM recommendation (RAM/chip/Metal aware).
- **Skills** system (8) + house **design system** + **design stage** for premium, agency-grade output.
- **RAG knowledge base** with real embeddings (`nomic-embed-text`) and keyword fallback.
- **Deep Research** — streamed multi-step web research → cited markdown report (keyless chain).
- **Deployment**: Netlify, HF Spaces, Vercel, Cloudflare Pages, Surge (+ custom domains), Docker/zip.
- **Workspace**: in-app code editor, zip download/upload, canvas preview.
- **History** persisted to SQLite (runs + full event streams); **presets**.
- **Plugins**: 17-server MCP catalog (npx + uvx), key passthrough, self-heal "repair", custom servers.
- **Gateway**: FreeLLMAPI dashboard in a native window.
- **UX**: 6 themes, command palette (⌘K), tabbed Settings, template gallery, maximized window.
- Cross-platform desktop **release workflow** (macOS/Windows/Linux); full docs suite.

### Fixed
- **Test loop**: `vitest` watch-mode made `npm test` hang → counted as failed → looped. Now forced
  one-shot (`CI=true` + `--run`); unrunnable test envs are skipped, not looped.
- **MCP catalog**: Python servers (fetch/git/time/sqlite) now use `uvx` (were failing on `npx`).
  Stale entries self-heal via a "repair" button.
- **Gateway**: opens in a native window (FreeLLMAPI blocks iframing); accurate backend status check.
- **Codegen**: robust delimited file format replaced fragile JSON; reformat retry.
- **Deep Research**: resilient keyless search chain after Jina search started requiring a key.
- **"No internet" / CSP**: loosened the Tauri CSP so the webview can reach https + preview external assets.
- Live `.env` re-read so saved keys apply without restarting the orchestrator.

### Native & release (0.2.0)
- Native menus, system tray, global hotkey ⌘⇧A, completion notifications.
- Keychain-backed secrets; live dev-server Canvas; real build-verify loop (apps compile + test).
- Qdrant vector store for RAG (with local fallback); per-project code RAG.
- Auto-updater (signed); cross-platform desktop release CI (macOS/Windows/Linux).

## [0.1.0] — initial
- Tauri + React desktop app, FastAPI orchestrator, five-stage pipeline, live streaming to the UI.
