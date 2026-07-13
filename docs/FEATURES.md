# DevFoundry — Features

Every capability, grouped by area. Endpoints are relative to `http://localhost:9100`.

## Pipeline (Forge)

- **Five stages** streamed live over WebSocket: Spec → Codebase → Tasks → Refine → Deploy.
- **Design stage** — before code, a "Lead Designer" produces a concrete design brief (palette,
  type scale, sections, components, tone) that the codegen must follow.
- **House design system** — every build targets React + Vite + TypeScript + Tailwind, mobile-first,
  responsive, accessible (WCAG AA), with real copy (no lorem ipsum) and a runnable test setup.
- **Skills** — selectable capability modules that steer the output: `premium-landing`,
  `saas-dashboard`, `ecommerce`, `portfolio`, `web-app-crud`, `docs-blog`, `a11y-first`, `seo-optimized`.
- **RAG knowledge base** — 16 curated design/engineering best-practices are semantically retrieved
  (Ollama `nomic-embed-text`, keyword fallback) and injected into codegen. Editable via `/api/knowledge`.
- **Robust codegen** — delimited `=== FILE: path ===` format (no JSON-escaping fragility), with a
  reformat retry. Handles weak and strong models.
- **Refine loop** — implements each task, then installs deps and runs tests **once** (CI mode, no
  watch-mode hangs); only iterates on genuine failures, and skips unrunnable test envs honestly.
- **Stop / Re-deploy** — stop a running pipeline; re-run just the deploy stage with a new target/domain.
- **Templates** — 12 starter ideas on the Forge page (landing, dashboard, e-commerce, API, …).

## Models & routing

- **24 providers** — Anthropic, OpenAI, OpenRouter, Groq, Google AI Studio, Mistral, Cerebras,
  Together, DeepSeek, Fireworks, Hugging Face, xAI, Perplexity, Moonshot, Zhipu, DashScope/Qwen,
  NVIDIA NIM, SambaNova, GitHub Models, **OpenCode Zen** (keyless via CLI auth), **FreeLLMAPI**,
  **Ollama**, **LM Studio**, and a **custom** OpenAI-compatible gateway.
- **Live model fetch** — `GET /api/llm/providers/{id}/models` hits the provider's real `/models`.
- **Per-provider keys** — entered on the Models page, stored in `.env`, **read live** (no restart).
- **Zero-config auto-detect** — with nothing configured, uses the first running local runtime.
- **MoE stage experts** — a different model per stage (`LLM_MODEL_SPEC/CODEGEN/TASKS/REFINE`).
- **Rotation / failover** — `LLM_ROTATION` chain, auto-retry on 429/5xx/timeout/unreachable.
- **Auto-router** — `GET /api/router/providers` lists connected providers (free vs paid) and a
  one-click "build rotation from all free providers".
- **Test LLM** — a button that runs a real completion through the full routing chain.
- **Your-machine picker** — detects RAM/cores/chip/Metal (`system_specs`) and recommends local
  models that fit (`POST /api/hardware/recommend`), with `ollama pull` commands and HF links.

## Deep Research

- **Streaming multi-step research** (`ws /api/research/ws`): plan sub-queries → search → read → cited report.
- **Keyless by default** — search chain: Brave/Tavily (if key) → SearXNG (bundled or local) → Wikipedia;
  reading via the keyless r.jina.ai reader with a direct-fetch fallback.
- **Markdown report** with sources; Copy and Download `.md`.

## Plugins (MCP)

- **17-server catalog**, one-click install — filesystem, memory, sequential-thinking, everything
  (npx); fetch, git, time, sqlite (uvx/Python); github, brave-search, tavily, playwright, puppeteer,
  postgres, context7, n8n, slack.
- **Key passthrough** — servers marked 🔑 read their token from `.env` on install.
- **Self-heal** — if an installed server's command drifts from the catalog, a "⟳ repair" button fixes it.
- **Custom servers** — stdio or HTTP transport. Browse tools, call tools (`/api/mcp/servers/{name}/call`).

## Deployment

- **Free cloud:** Netlify, Hugging Face Spaces, Vercel, Cloudflare Pages, Surge — **custom domains**
  for Netlify & Surge.
- **Local:** Docker image (when a Dockerfile exists), or a zip bundle (always works as a fallback).
- **Per-run target/domain**, or global default in Settings. Graceful zip fallback on any cloud error.

## Project workspace

- **Code editor** — file tree + text editor (⌘S), for every generated project.
- **Download / upload** — export the project as a zip, or upload a zip back into a run.
- **Canvas preview** — a sandboxed iframe that inlines local CSS/JS to preview a static frontend, plus
  a "deployed site" tab.

## History & persistence

- Every run and its full event stream are saved to `workspace/devfoundry.db` (SQLite) and survive
  restarts. Browse, replay, or delete from the **History** page.
- **Presets** — save/apply provider+model+rotation+deploy configs (`workspace/presets.json`).

## Gateway

- Embeds the **FreeLLMAPI dashboard** (`localhost:3002`) in a native child window (its
  `X-Frame-Options` blocks iframing), with an accurate backend status check.

## Appearance & UX

- **6 themes** (Midnight, Ocean, Forest, Grape, Nord, Paper-light) — instant, persisted.
- **Command palette** (⌘K) — navigate and switch themes.
- **Maximized** window, sidebar navigation, live service-health bar.

## Bundled infra (isolated mode)

`docker-compose` includes the five framework sidecars plus **SearXNG** (`:8100`, JSON API for research)
and **Qdrant** (`:6333`, vector DB) — managed by the app's Services page, not external.
