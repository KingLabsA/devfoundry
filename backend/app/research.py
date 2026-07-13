"""Deep Research: multi-step web research → cited report.

Keyless by default:
- Search: local SearXNG (SEARXNG_URL or http://localhost:8082), format=json
- Read:   direct fetch + HTML-to-text; r.jina.ai used only if JINA_API_KEY is set
The LLM (via the configured provider) plans sub-queries and writes the report.
"""
import asyncio
import logging
import re
from typing import Any, Callable, Awaitable

import httpx

from app.config import env_value
from app.llm import complete

log = logging.getLogger(__name__)

Progress = Callable[[str], Awaitable[None]]


def _searxng_url() -> str:
    return (env_value("SEARXNG_URL") or "http://localhost:8082").rstrip("/")


async def _searxng(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    resp = await client.get(f"{_searxng_url()}/search", params={"q": query, "format": "json"})
    resp.raise_for_status()
    data = resp.json()
    out = [{"title": it.get("title", ""), "url": it["url"], "snippet": (it.get("content") or "")[:400]}
           for it in data.get("results", [])[:limit] if it.get("url")]
    for ib in data.get("infoboxes", [])[:2]:
        urls = ib.get("urls", [])
        if urls and urls[0].get("url"):
            out.append({"title": ib.get("infobox", ""), "url": urls[0]["url"],
                        "snippet": (ib.get("content") or "")[:400]})
    return out


async def _brave(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    key = env_value("BRAVE_API_KEY")
    if not key:
        return []
    resp = await client.get("https://api.search.brave.com/res/v1/web/search",
                            params={"q": query, "count": limit},
                            headers={"X-Subscription-Token": key, "Accept": "application/json"})
    resp.raise_for_status()
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": (r.get("description") or "")[:400]}
            for r in resp.json().get("web", {}).get("results", [])[:limit] if r.get("url")]


async def _tavily(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    key = env_value("TAVILY_API_KEY")
    if not key:
        return []
    resp = await client.post("https://api.tavily.com/search",
                             json={"api_key": key, "query": query, "max_results": limit})
    resp.raise_for_status()
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": (r.get("content") or "")[:400]}
            for r in resp.json().get("results", [])[:limit] if r.get("url")]


async def _wikipedia(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    resp = await client.get("https://en.wikipedia.org/w/api.php",
                            params={"action": "query", "list": "search", "srsearch": query,
                                    "format": "json", "srlimit": limit})
    resp.raise_for_status()
    out = []
    for r in resp.json().get("query", {}).get("search", [])[:limit]:
        title = r.get("title", "")
        snippet = re.sub(r"<[^>]+>", "", r.get("snippet", ""))
        out.append({"title": title, "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "snippet": snippet[:400]})
    return out


async def _search(query: str, limit: int = 5) -> list[dict]:
    """Resilient search chain: Brave/Tavily (if key) → SearXNG → Wikipedia fallback."""
    ua = {"User-Agent": "DevFoundry/0.1 (research; +https://github.com/devfoundry)"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=ua) as client:
        for name, fn in (("brave", _brave), ("tavily", _tavily), ("searxng", _searxng)):
            try:
                results = await fn(client, query, limit)
                if results:
                    return results
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                log.info("search[%s] no results for %r: %s", name, query, exc)
        try:
            return await _wikipedia(client, query, limit)
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("all search backends failed for %r: %s", query, exc)
            return []


_TAG = re.compile(r"<(script|style)[\s\S]*?</\1>|<[^>]+>")
_WS = re.compile(r"\n{3,}")


async def _read(url: str, max_chars: int = 6000) -> str:
    """Read a page as clean text via the keyless r.jina.ai reader; direct fetch fallback."""
    jina_key = env_value("JINA_API_KEY")
    headers = {"Authorization": f"Bearer {jina_key}"} if jina_key else {}
    async with httpx.AsyncClient(timeout=35, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 DevFoundry"}) as client:
        try:
            resp = await client.get(f"https://r.jina.ai/{url}", headers=headers)
            resp.raise_for_status()
            return resp.text[:max_chars]
        except httpx.HTTPError:
            pass
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            text = _TAG.sub(" ", resp.text)
            return _WS.sub("\n\n", re.sub(r"[ \t]{2,}", " ", text)).strip()[:max_chars]
        except httpx.HTTPError as exc:
            log.warning("read failed for %s: %s", url, exc)
            return ""


async def deep_research(question: str, on_progress: Progress, depth: int = 4, read_top: int = 3) -> dict[str, Any]:
    await on_progress(f"Planning research for: {question}")
    plan_raw = await complete(
        f"Break this research question into {depth} focused web-search queries. "
        f"Return ONLY the queries, one per line, no numbering.\n\nQuestion: {question}",
        "You are a research strategist.", max_tokens=400, role="tasks")
    queries = [q.strip("-*0123456789. ").strip() for q in plan_raw.splitlines() if q.strip()][:depth]
    if not queries:
        queries = [question]
    await on_progress(f"Search plan: {', '.join(queries)}")

    results = await asyncio.gather(*(_search(q) for q in queries))
    sources: dict[str, dict] = {}
    for group in results:
        for r in group:
            sources.setdefault(r["url"], r)
    await on_progress(f"Found {len(sources)} unique sources")

    top = list(sources.values())[: max(read_top, 1)]
    for s in top:
        await on_progress(f"Reading: {s['title'] or s['url']}")
        s["content"] = await _read(s["url"])

    corpus = "\n\n".join(
        f"[{i+1}] {s.get('title','')} — {s['url']}\n{s.get('content') or s.get('snippet','')}"
        for i, s in enumerate(sources.values()))[:24000]
    await on_progress("Synthesizing cited report…")
    report = await complete(
        f"Write a thorough, well-structured research report answering:\n{question}\n\n"
        f"Use ONLY these sources; cite them inline as [n]. End with a 'Sources' list.\n\n{corpus}",
        "You are a meticulous research analyst. Be accurate and cite every claim.",
        max_tokens=6000, role="spec")

    cited = sorted(set(int(n) for n in re.findall(r"\[(\d+)\]", report)))
    src_list = list(sources.values())
    used = [{"n": n, "title": src_list[n-1].get("title", ""), "url": src_list[n-1]["url"]}
            for n in cited if 1 <= n <= len(src_list)]
    await on_progress("Report complete")
    return {"question": question, "queries": queries, "report": report,
            "sources": used or [{"n": i+1, **s} for i, s in enumerate(src_list)]}
