"""Qdrant-backed vector store (REST API) with an in-process fallback.

When Qdrant is reachable (bundled at :6333 in the Docker stack, or standalone), it's used
for knowledge + per-project code retrieval. Otherwise callers fall back to their local path.
No extra dependency — talks to Qdrant's HTTP API with httpx.
"""
import logging
import time

import httpx

from app.config import env_value

log = logging.getLogger(__name__)

_state = {"ts": 0.0, "up": False}


def qdrant_url() -> str:
    return (env_value("QDRANT_URL") or "http://localhost:6333").rstrip("/")


async def available() -> bool:
    """Cached liveness check (10s)."""
    if time.time() - _state["ts"] < 10:
        return _state["up"]
    up = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{qdrant_url()}/collections")
            up = resp.status_code == 200
    except httpx.HTTPError:
        up = False
    _state.update(ts=time.time(), up=up)
    return up


async def ensure_collection(name: str, size: int) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        exists = await client.get(f"{qdrant_url()}/collections/{name}")
        if exists.status_code == 200:
            return
        await client.put(f"{qdrant_url()}/collections/{name}",
                         json={"vectors": {"size": size, "distance": "Cosine"}})


async def upsert(name: str, points: list[dict]) -> None:
    """points: [{id:int, vector:[...], payload:{...}}]"""
    if not points:
        return
    async with httpx.AsyncClient(timeout=30) as client:
        await client.put(f"{qdrant_url()}/collections/{name}/points?wait=true",
                         json={"points": points})


async def search(name: str, vector: list[float], k: int = 6) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{qdrant_url()}/collections/{name}/points/search",
                                 json={"vector": vector, "limit": k, "with_payload": True})
        if resp.status_code != 200:
            return []
        return [hit.get("payload", {}) for hit in resp.json().get("result", [])]


async def delete_collection(name: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(f"{qdrant_url()}/collections/{name}")
    except httpx.HTTPError:
        pass
