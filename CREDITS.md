# Credits & Acknowledgments

DevFoundry is created by **King3Djbl** of **KingLabs** and built with
[Claude Code](https://claude.com/claude-code) (Anthropic). MIT licensed — see [LICENSE](LICENSE).

**Find the author:**
[GitHub — KingLabsA](https://github.com/KingLabsA?tab=repositories) ·
[Hugging Face — King3Djbl](https://huggingface.co/King3Djbl) ·
[Ollama — FableForge-AI](https://ollama.com/FableForge-AI)

It stands on excellent open source. Thank you to every one of these projects:

## Core stack

| Project | Role | License |
|---|---|---|
| [Tauri](https://tauri.app) | Native desktop shell, menus/tray/updater plugins | MIT/Apache-2.0 |
| [React](https://react.dev) + [Vite](https://vitejs.dev) | Frontend UI | MIT |
| [TypeScript](https://www.typescriptlang.org) | Frontend language | Apache-2.0 |
| [FastAPI](https://fastapi.tiangolo.com) + [Uvicorn](https://www.uvicorn.org) | Embedded orchestrator | MIT / BSD-3 |
| [httpx](https://www.python-httpx.org) | Async HTTP client | BSD-3 |
| [react-markdown](https://github.com/remarkjs/react-markdown) + [remark-gfm](https://github.com/remarkjs/remark-gfm) | Report/artifact rendering | MIT |
| [Rust](https://www.rust-lang.org) | Native commands | MIT/Apache-2.0 |

## Models & AI infrastructure

| Project | Role |
|---|---|
| [Ollama](https://ollama.com) | Local model runtime + embeddings (`nomic-embed-text`) |
| [LM Studio](https://lmstudio.ai) | Local model runtime |
| [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) by tashfeenahmed | Self-hosted unified free-LLM gateway |
| [OpenCode](https://opencode.ai) | Zen model gateway + refinement CLI |
| [Model Context Protocol](https://modelcontextprotocol.io) | Plugin standard; reference servers in the catalog |
| [Qdrant](https://qdrant.tech) | Bundled vector store for RAG |
| [SearXNG](https://docs.searxng.org) | Bundled metasearch for Deep Research |
| [Jina Reader](https://jina.ai/reader) | Keyless page-to-text extraction |
| [Hugging Face](https://huggingface.co) | Model hub, GGUF distribution, Spaces deploys |
| [Nomic](https://www.nomic.ai) | `nomic-embed-text` embedding model |

Provider APIs the router can use: Anthropic, OpenAI, OpenRouter, Groq, Google AI Studio, Mistral,
Cerebras, Together, DeepSeek, Fireworks, xAI, Perplexity, Moonshot, Zhipu, Alibaba DashScope,
NVIDIA NIM, SambaNova, GitHub Models.

## Generated-app stack

Generated projects target [Tailwind CSS](https://tailwindcss.com), [Vitest](https://vitest.dev),
and [Testing Library](https://testing-library.com).

## Deployment targets

[Netlify](https://www.netlify.com), [Vercel](https://vercel.com),
[Cloudflare Pages](https://pages.cloudflare.com), [Surge](https://surge.sh),
[Hugging Face Spaces](https://huggingface.co/spaces), [Docker](https://www.docker.com).

## Inspiration

The multi-role pipeline draws on ideas from [MetaGPT](https://github.com/FoundationAgents/MetaGPT)
(software-company simulation) and [bolt.diy](https://github.com/stackblitz-labs/bolt.diy)
(idea-to-app generation). The reasoning modes implement Mixture-of-Agents, Self-MoA, and
Tree-of-Thoughts patterns from the research literature.

---

If your project is listed here and you'd like a correction, please open an issue.
