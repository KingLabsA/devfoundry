# Changelog

All notable changes to DevFoundry. Format loosely follows Keep a Changelog.

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
