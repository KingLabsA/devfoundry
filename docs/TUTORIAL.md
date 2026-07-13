# DevFoundry Tutorial

From zero to a deployed app. Three paths by setup level.

---

## Path 1 — First run (zero config)

The app is self-contained: it spawns its own orchestrator on launch.

1. **Launch DevFoundry.** The header service dots turn green within ~10s.
2. **Give it a brain.** Two options:
   - *Local, free:* run `ollama serve` (or LM Studio, or FreeLLMAPI on :3002). DevFoundry auto-detects it.
   - *Cloud:* open **Models** → paste a key next to any provider → click **Use**.
   - Not sure it's working? Models → **⚡ Test LLM** runs a real completion through the routing chain.
3. **Forge.** On the **Forge** page: pick one or more **Skills** (try *Premium landing page*), type an
   idea (`⌘↵` to submit), and watch the five stages stream.
4. **Inspect the result.** Switch to the **Code** tab (file tree + editor) and **Canvas** tab (live
   preview). Download the project as a zip from the Code toolbar.
5. **Find it later.** The **History** page lists every run and replays its full log.

### Recommended local model for your machine

Open **Models** → the "Your machine" card detects your RAM/chip and recommends models that fit
(e.g. 24GB Apple Silicon → `qwen2.5-coder:14b`). Copy the `ollama pull …` command, then click **Use** on Ollama.

---

## Path 2 — Premium output + free deploy

1. **Better model.** For agency-grade output, use a strong model — a local coder model
   (`qwen2.5-coder`), FreeLLMAPI `auto`, or a cloud provider on the Models page.
2. **Skills.** On Forge, select the skills that match the product (e.g. *Premium landing page* +
   *SEO-optimized*, or *SaaS dashboard*). These inject expert design + structure guidance.
3. **Deploy target.** In the Deploy bar (Forge) or Settings → Deployment, pick a free target:
   - **Surge** / **Netlify** — static hosting, support a **custom domain**.
   - **Vercel** / **Cloudflare Pages** / **Hugging Face Spaces** — free tiers.
   - Add the provider's free token in Settings → Deployment. No token? It falls back to a zip bundle.
4. **Forge & deploy.** Run it; the deploy stage publishes and shows the URL. Use **Re-deploy** to
   push again to a different target/domain.

---

## Path 3 — Deep Research

1. Open **Research**. Search works keyless (SearXNG → Wikipedia). For real web search, add a free
   **Brave** or **Tavily** key in Settings → Research.
2. Ask a question, choose depth (2–6 sub-queries), and **Research**. Watch it plan → search → read →
   synthesize.
3. Read the cited markdown report; **Copy** or **Download .md**.

---

## Enabling true RAG embeddings

The knowledge base that improves codegen uses embeddings when available:

```bash
ollama pull nomic-embed-text
```

Then it retrieves best-practices semantically (cosine similarity) rather than by keyword. Configure
via `OLLAMA_BASE_URL` / `EMBED_MODEL` in Settings → Advanced (raw .env).

---

## Optional: Docker "isolated mode"

The default embedded mode needs no Docker. If you want the containerized engines, bundled **SearXNG**
(working web search), and **Qdrant** (vector DB):

1. **Services** page → **▶ Start All**. DevFoundry launches Docker Desktop if needed and brings the
   stack up (first run builds images — several minutes; watch per-service **logs**).
2. Research then uses the bundled SearXNG on `:8100` automatically.

---

## Developing DevFoundry

```bash
# backend (hot reload) — embedded mode
cd backend && .venv/bin/uvicorn app.main:app --port 9100 --reload

# desktop app (hot reload, opens its own window)
cd frontend && npm run tauri dev

# tests
cd backend && .venv/bin/python -m pytest
cd frontend && npx tsc --noEmit
```

Set `DEVFOUNDRY_MOCK=1` on the backend for an instant, deterministic scripted pipeline (great for UI
work and demos — no tokens spent).

---

## Recording a demo

See [DEMO.md](DEMO.md) for shot-by-shot social-media scripts (Show HN, X thread, YouTube walkthrough).
