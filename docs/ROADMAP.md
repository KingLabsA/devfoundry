# Roadmap & Status

Honest assessment of what's done and what's next. Severity: 🔴 launch-blocking · 🟡 important · 🟢 polish.

## Shipped

- Native desktop app (Tauri): Forge, Research, History, Models, Plugins, Gateway, Services, Settings,
  command palette, 6 themes.
- **Embedded mode** — the whole pipeline runs in-process; app auto-starts the orchestrator; **no Docker
  required**. Isolated Docker mode optional (with bundled SearXNG + Qdrant).
- Pipeline: spec + **design stage**, robust delimited codegen, **skills** system, **RAG** knowledge base
  (real embeddings), refine with **fixed** one-shot test runs, stop/redeploy.
- Models: **24 providers**, live model fetch, zero-config auto-detect, MoE stage experts, rotation,
  auto-router, hardware-based local-LLM recommender, keyless OpenCode Zen, FreeLLMAPI.
- Deploy: Netlify, HF Spaces, Vercel, Cloudflare Pages, Surge (+ custom domains), Docker/zip; graceful fallback.
- Workspace: code editor, download/upload, canvas preview. History persisted to SQLite. Presets.
- Plugins: 17-server MCP catalog (npx + uvx), key passthrough, self-heal, custom servers, tool calling.
- Deep Research: streamed multi-step, keyless search chain, cited markdown report + export.
- Docs suite + landing page; cross-platform desktop release workflow.

## Next

### 🔴 Signed / notarized builds
Ad-hoc signature triggers Gatekeeper/SmartScreen warnings. Needs Apple Developer ID + notarization and
Windows code signing in the release workflow.

### 🟡 Build-verify loop that makes tests *pass*
Refine currently runs tests once and skips unrunnable envs. Next: actually run `npm install && vitest run`
during refine, feed real failures back to the model, and iterate until green — so generated apps ship
with passing tests, not skipped ones.

### 🟡 True agentic memory (RAG over the workspace)
The knowledge base is curated best-practices. Add per-project RAG: embed the generated codebase into
Qdrant and let refine retrieve relevant files for context on large projects.

### 🟡 Provider keys in the OS keychain
`.env` is standard for dev tools but the desktop bar is higher. Move secrets to Keychain/Credential
Manager with `.env` as fallback.

### 🟢 More
Windows/Linux CI artifacts published on every tag; auto-update (`tauri-plugin-updater`); richer Canvas
(run generated dev servers, not just static preview); a template marketplace; MCP tools wired *into* the
pipeline (e.g. a DB MCP the refine stage can query); crash reporting; onboarding wizard.

## Known limitations (be upfront)

- Output quality tracks the chosen model; tiny models produce rough drafts.
- Deep Research is best with a free Brave/Tavily key; the pure-keyless path leans on Wikipedia.
- Runs live in memory + SQLite; a mid-run backend restart cancels the in-flight task (files persist;
  finish with Re-deploy).
