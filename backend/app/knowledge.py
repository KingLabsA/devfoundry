"""RAG knowledge base: curated design/engineering best-practices retrieved and
injected into the codegen context, so the pipeline builds on expert patterns.

Uses Ollama embeddings (nomic-embed-text) + cosine similarity when available;
falls back to keyword scoring. Stored in <workspace>/knowledge.db.
"""
import json
import logging
import math
import re
import sqlite3
import threading

import httpx

from app.config import env_value, get_settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

# Curated knowledge — expanded, high-signal snippets the generator can lean on.
SEED: list[dict] = [
    {"topic": "landing-hero", "text": "A landing hero converts when it states a specific outcome in "
     "the headline, a one-line subhead on how, one primary CTA above the fold, and a supporting visual. "
     "Avoid vague taglines. Add a trust strip (logos, ratings) immediately below."},
    {"topic": "pricing", "text": "Pricing tables work best with 3 tiers, the middle 'recommended' one "
     "visually elevated, monthly/annual toggle, feature checklists, and a clear CTA per tier. Anchor "
     "value with the highest tier."},
    {"topic": "layout-spacing", "text": "Premium feel comes from generous whitespace: section padding "
     "py-16 to py-24, consistent 4/8px spacing scale, max-w-7xl centered content, and a strong type "
     "hierarchy. Cramped layouts read as cheap."},
    {"topic": "color-system", "text": "Use one brand color plus a neutral slate scale. Derive hover/active "
     "shades systematically. Ensure WCAG AA contrast (4.5:1 for text). Subtle gradients and soft shadows "
     "add depth without noise."},
    {"topic": "typography", "text": "Limit to 1-2 typefaces. Establish a modular scale (e.g., 1.25 ratio). "
     "Body text 16-18px, line-height 1.6, measure 60-75 chars. Headings tight tracking, bold weight."},
    {"topic": "responsive", "text": "Design mobile-first. Stack columns on small screens, use CSS grid/flex "
     "with responsive breakpoints, fluid images, and touch-friendly 44px targets. Test at 375/768/1280."},
    {"topic": "forms-ux", "text": "Forms need clear labels, inline validation, helpful error text, disabled "
     "states during submit, and success feedback. Group related fields; minimize required inputs."},
    {"topic": "dashboard-ux", "text": "Dashboards lead with a KPI stat row, then charts, then detailed "
     "tables. Provide filters, sort, empty states, and skeleton loaders. Keep density legible with spacing."},
    {"topic": "accessibility", "text": "Use semantic HTML, label every control, provide alt text, maintain "
     "focus order, visible focus rings, keyboard operability, and prefers-reduced-motion support."},
    {"topic": "performance", "text": "Ship fast: code-split routes, lazy-load images (loading=lazy), "
     "minimize JS, use system fonts or preloaded webfonts, and cache static assets."},
    {"topic": "seo", "text": "SEO essentials: unique title/description per page, semantic headings (one h1), "
     "Open Graph + Twitter cards, descriptive alt text, clean URLs, and JSON-LD structured data."},
    {"topic": "react-structure", "text": "Structure React apps by feature: components/ for reusable UI, "
     "one component per file, colocate styles, lift shared state, keep components small and typed."},
    {"topic": "api-design", "text": "REST APIs: resource-oriented URLs, correct status codes, consistent "
     "JSON envelopes, input validation, pagination for lists, and clear error bodies."},
    {"topic": "testing", "text": "Cover critical paths: unit tests for logic, component tests for UI states, "
     "and at least one happy-path integration test. Keep tests fast and deterministic."},
    {"topic": "microcopy", "text": "Great products use specific, human microcopy: button labels describe the "
     "action ('Start free trial', not 'Submit'), empty states guide next steps, errors are actionable."},
    {"topic": "motion", "text": "Motion should be purposeful: 150-250ms transitions on hover/focus, subtle "
     "lifts and fades, respect reduced-motion. Avoid autoplaying or distracting animation."},
]


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = get_settings().devfoundry_workspace / "knowledge.db"
        _conn = sqlite3.connect(str(path), check_same_thread=False)
        _conn.execute("""CREATE TABLE IF NOT EXISTS kb (
            id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, text TEXT, embedding TEXT)""")
        _conn.commit()
        if not _conn.execute("SELECT 1 FROM kb LIMIT 1").fetchone():
            for item in SEED:
                _conn.execute("INSERT INTO kb (topic, text, embedding) VALUES (?,?,?)",
                              (item["topic"], item["text"], ""))
            _conn.commit()
            log.info("seeded knowledge base with %d entries", len(SEED))
    return _conn


async def _embed(text: str) -> list[float] | None:
    base = env_value("OLLAMA_BASE_URL") or "http://localhost:11434"
    model = env_value("EMBED_MODEL") or "nomic-embed-text"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{base}/api/embeddings", json={"model": model, "prompt": text})
            resp.raise_for_status()
            return resp.json().get("embedding")
    except (httpx.HTTPError, ValueError):
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def add_entry(topic: str, text: str) -> None:
    with _lock:
        db = _db()
        db.execute("INSERT INTO kb (topic, text, embedding) VALUES (?,?,?)", (topic, text, ""))
        db.commit()


def list_entries() -> list[dict]:
    with _lock:
        rows = _db().execute("SELECT id, topic, text FROM kb ORDER BY id").fetchall()
    return [{"id": r[0], "topic": r[1], "text": r[2]} for r in rows]


async def retrieve(query: str, k: int = 5) -> list[dict]:
    """Return the k most relevant KB entries (embeddings if available, else keyword)."""
    with _lock:
        rows = _db().execute("SELECT id, topic, text, embedding FROM kb").fetchall()
    qvec = await _embed(query)
    scored: list[tuple[float, dict]] = []
    if qvec:
        for rid, topic, text, emb in rows:
            if not emb:
                vec = await _embed(text)
                if vec:
                    with _lock:
                        _db().execute("UPDATE kb SET embedding=? WHERE id=?", (json.dumps(vec), rid))
                        _db().commit()
                    emb = json.dumps(vec)
            if emb:
                scored.append((_cosine(qvec, json.loads(emb)), {"topic": topic, "text": text}))
    if not scored:  # keyword fallback
        terms = set(re.findall(r"[a-z]{4,}", query.lower()))
        for rid, topic, text, _ in rows:
            hay = (topic + " " + text).lower()
            scored.append((sum(1 for t in terms if t in hay), {"topic": topic, "text": text}))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [item for score, item in scored[:k] if score > 0] or [s[1] for s in scored[:k]]


async def context_for(idea: str) -> str:
    entries = await retrieve(idea, k=6)
    if not entries:
        return ""
    return "RELEVANT BEST-PRACTICES (apply these):\n" + "\n".join(
        f"- [{e['topic']}] {e['text']}" for e in entries)
