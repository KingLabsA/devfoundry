# Changelog

All notable changes to DevFoundry. Format loosely follows Keep a Changelog.

## [Unreleased]

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

## [0.1.0] — initial
- Tauri + React desktop app, FastAPI orchestrator, five-stage pipeline, live streaming to the UI.
