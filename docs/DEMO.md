# DevFoundry — Demo & Social Scripts

Shot-by-shot scripts for recording demos. Use **demo mode** for deterministic, fast,
token-free runs: start the backend with `DEVFOUNDRY_MOCK=1`, or for real output use a
fast local/coder model.

Setup for recording: resize the window to ~1280×800, pick the **Midnight** theme (or record
one clip per theme to show the switcher), and clear History first for a clean slate.

---

## 1. The 60-second hook (X / TikTok / Reels)

**Goal:** idea → deployed app, fast. Vertical or square crop works.

| t | Shot | On-screen text |
|---|------|----------------|
| 0:00 | Forge page, cursor in the idea box | "Type an app idea." |
| 0:03 | Click **Premium landing page** skill, type *"landing page for a coffee subscription"* | "Pick a skill." |
| 0:06 | Hit **Forge It**; timeline lights up Spec→Deploy | "Watch it build." |
| 0:20 | Cut to **Artifacts** → design brief (markdown) | "It designs first." |
| 0:28 | Cut to **Code** tab → file tree of a real React+Tailwind app | "Real code. 20+ files." |
| 0:38 | **Canvas** tab → the rendered landing page | "And it runs." |
| 0:48 | Deploy log shows a URL / zip | "Deployed. Free." |
| 0:55 | Sidebar pan: Research, Models, Plugins, Gateway | "All local. Your models." |

**Caption:** "Local-first AI app factory. Idea in → designed, coded, tested, deployed app out.
24 model providers or fully offline. Open source. ⬢ DevFoundry"

---

## 2. Show HN / Reddit r/LocalLLaMA post

**Title:** *Show HN: DevFoundry — a local-first desktop app that runs an AI software factory*

**Body beats:**
- The problem: cloud AI builders lock you in and take your code. DevFoundry runs entirely on your machine.
- 90-second demo video (script #1 or #3).
- Emphasize for r/LocalLLaMA: **auto-detects Ollama/LM Studio/FreeLLMAPI**, MoE stage experts,
  rotation across free providers, and a "your machine → best local model" recommender.
- Link the repo + the one-command demo-mode try.
- Be in the thread for the first 4 hours.

**r/LocalLLaMA angle:** lead with the local story — show it picking `qwen2.5-coder:14b` for a 24GB
Mac and running the whole pipeline offline, then a Deep Research pass with no API keys.

---

## 3. YouTube walkthrough (5 min)

1. **Cold open (0:00–0:20):** one forge run in fast-forward, ending on the Canvas preview.
2. **Local models (0:20–1:20):** Models page — the "your machine" recommender, `ollama pull`,
   click Use, ⚡ Test LLM. Mention 24 providers and auto-detect.
3. **Skills & design (1:20–2:20):** pick skills, forge, open the design brief + the component-per-file
   structure in Code, preview in Canvas.
4. **Deploy (2:20–3:00):** pick Surge/Netlify, add a token, deploy, open the live URL.
5. **Deep Research (3:00–3:50):** ask a question, watch the streamed steps, read the cited report.
6. **Plugins + Gateway (3:50–4:30):** install an MCP server one-click; open the FreeLLMAPI dashboard.
7. **Wrap (4:30–5:00):** History persistence, themes (⌘K), "everything ran on my laptop."

---

## 4. Screenshot set (for the repo / landing page)

Capture these at 1280×800:
1. **Forge mid-run** — timeline active, live log streaming.
2. **Code tab** — file tree of a generated React+Tailwind app + a component open.
3. **Canvas** — the rendered app.
4. **Models** — provider list + "your machine" recommender.
5. **Research** — a finished cited report.
6. **Plugins** — the MCP catalog with green "connected" servers.

Drop them in `website/screenshots/` and reference from `website/index.html`.

---

## Talking points (accurate — don't overclaim)

- ✅ Local-first, your keys/code never leave the machine.
- ✅ 24 providers incl. keyless (OpenCode Zen) and fully local (Ollama/LM Studio).
- ✅ Streams every stage; persists all runs; free deploys.
- ⚠️ Output quality tracks the model you choose — say so. A strong coder model gives agency-grade
  results; a tiny model gives a rough draft.
- ⚠️ Deep Research is keyless-capable but best with a free Brave/Tavily key (this environment's
  local SearXNG engines may be rate-limited).
