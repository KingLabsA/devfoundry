<div align="center">

# ⬢ DevFoundry

**Type an app idea. Get a designed, coded, tested, and deployed application — while you watch.**

A local-first, native desktop app that runs an autonomous software factory on your own machine.
Bring your own models (24 providers, or fully local), watch every step stream live, and deploy free.

[Features](docs/FEATURES.md) · [Tutorial](docs/TUTORIAL.md) · [Architecture](docs/ARCHITECTURE.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Demo scripts](docs/DEMO.md) · [Roadmap](docs/ROADMAP.md)

</div>

---

## What it does

Describe an app in plain language. DevFoundry runs a multi-stage pipeline and streams the whole thing to the UI:

| Stage      | What happens                                                        |
|------------|--------------------------------------------------------------------|
| **Spec**   | PRD, system architecture, and API spec — plus a **design brief** from a "Lead Designer" |
| **Codebase** | A complete, production-grade app (React + Vite + TypeScript + Tailwind) following a house design system |
| **Tasks**  | Feature breakdown assigned to AI developer agents                  |
| **Refine** | Each task implemented; tests installed and run; fixes iterated     |
| **Deploy** | Packaged and deployed (free targets or local)                      |

Every run — docs, code, diffs, test output, deploy logs — is **saved to SQLite** and browsable in History.

## Why it's different

- **Local-first.** Ideas, API keys, and generated code never leave your machine.
- **Runs inside the app.** The orchestrator auto-starts on launch. **No Docker required** for the default embedded mode — Docker is optional ("isolated mode") for containerized engines/deploys.
- **Bring your own models — 24 providers.** Anthropic, OpenAI, OpenRouter, Groq, Google, Mistral, Cerebras, Together, DeepSeek, Fireworks, HF, xAI, Perplexity, Moonshot, Zhipu, Qwen, NVIDIA, SambaNova, GitHub Models, **OpenCode Zen** (keyless free), **FreeLLMAPI**, **Ollama** & **LM Studio** (local), and any custom gateway.
- **Zero-config.** Nothing set up? It **auto-detects** a running local runtime (FreeLLMAPI → Ollama → LM Studio) and just works.
- **Smart routing.** MoE stage experts (a different model per stage), automatic **rotation/failover** on rate limits, and a one-click auto-router built from every free provider you have.
- **Premium output.** A skills system + house design system + RAG knowledge base push generated apps to agency quality — real content, responsive, accessible, Tailwind.
- **Free deployment, built in.** Netlify, Hugging Face Spaces, Vercel, Cloudflare Pages, Surge — plus local Docker/zip. Custom domains supported.

## Platforms

Native **desktop** app (Tauri) — not mobile or web. Same codebase ships to all three desktop OSes via CI ([.github/workflows/release.yml](.github/workflows/release.yml)):

| OS | Bundles | Status |
|----|---------|--------|
| macOS (Apple Silicon + Intel) | `.app`, `.dmg` | built locally + CI |
| Windows | `.msi`, `.exe` | CI |
| Linux | `.deb`, `.AppImage` | CI |

## Install

Download the latest `.dmg` / `.msi` / `.AppImage` from Releases. Or build from source:

```bash
git clone <repo-url> devfoundry && cd devfoundry
cd frontend && npm install && npm run tauri build
# bundles land in frontend/src-tauri/target/release/bundle/
```

**Requirements:** a desktop OS; Node 20+ and Rust (to build from source); Python 3.11+ (the app spawns the orchestrator — a `.venv` under `backend/` is used if present). Docker and API keys are **optional**.

## Quick start (60 seconds)

1. Launch DevFoundry — the orchestrator auto-starts (header dots go green).
2. **Models** page → click **Use** on a provider (or just rely on auto-detect if you run Ollama/FreeLLMAPI).
3. **Forge** page → pick **Skills** (e.g. *Premium landing page*) → type an idea → **Forge It**.
4. Watch the pipeline stream. Browse the result in the **Code** and **Canvas** tabs; find it later in **History**.

Full walkthrough: [docs/TUTORIAL.md](docs/TUTORIAL.md).

## The app at a glance

| Page | What it's for |
|------|---------------|
| **Forge** | Describe an idea, pick skills + deploy target, watch the pipeline; Code editor & Canvas preview |
| **Research** | Deep Research — multi-step web research → cited report (markdown, exportable) |
| **History** | Every past build, persisted; replay its event log |
| **Models** | 24 providers, fetch/activate models, MoE routing, rotation, **your-machine local-LLM picker**, auto-router |
| **Plugins** | One-click MCP server catalog (17 servers) + custom servers + deploy providers |
| **Gateway** | The FreeLLMAPI dashboard, in a native window |
| **Services** | Optional Docker "isolated mode" lifecycle |
| **Settings** | Tabbed: General, Providers, Deployment, Research, Appearance (themes), Advanced (presets, raw .env) |

Press **⌘K** anywhere for the command palette (navigate + switch theme).

## Docs

- **[Features](docs/FEATURES.md)** — every capability, in detail
- **[Tutorial](docs/TUTORIAL.md)** — first run, local models, real deploy, dev mode
- **[Architecture](docs/ARCHITECTURE.md)** — how the pieces fit
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — common issues & fixes
- **[Demo scripts](docs/DEMO.md)** — social-media walkthroughs & storyboards
- **[Roadmap](docs/ROADMAP.md)** — what's next
- **[Contributing](CONTRIBUTING.md)** · **[Changelog](CHANGELOG.md)**

## License

MIT — see [LICENSE](LICENSE).
