"""Deep Research (streamed), gateway status, and config presets."""
import json
import logging

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.config import env_value, get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ---------------------------------------------------------------- gateway
@router.get("/gateway/status")
async def gateway_status() -> dict:
    url = env_value("FREELLMAPI_URL") or "http://localhost:3002"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            resp = await client.get(url)
        return {"up": resp.status_code < 500, "url": url, "status": resp.status_code}
    except httpx.RequestError:
        return {"up": False, "url": url, "status": 0}


# ---------------------------------------------------------------- deep research (WS)
@router.websocket("/research/ws")
async def research_ws(ws: WebSocket) -> None:
    await ws.accept()
    try:
        req = json.loads(await ws.receive_text())
        question = (req.get("question") or "").strip()
        if len(question) < 8:
            await ws.send_text(json.dumps({"type": "error", "message": "question too short"}))
            return

        async def progress(msg: str) -> None:
            await ws.send_text(json.dumps({"type": "step", "message": msg}))

        from app.llm import LLMNotConfigured
        from app.research import deep_research
        try:
            result = await deep_research(question, progress,
                                         depth=int(req.get("depth", 4)),
                                         read_top=int(req.get("read_top", 3)))
            await ws.send_text(json.dumps({"type": "result", **result}))
        except LLMNotConfigured as exc:
            await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception as exc:  # noqa: BLE001
            log.exception("research failed")
            await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except RuntimeError:
            pass


# ---------------------------------------------------------------- embedded services (no Docker)
@router.get("/embedded/qdrant/status")
async def qdrant_status() -> dict:
    from app import embedded_services
    return await embedded_services.status()


@router.post("/embedded/qdrant/install")
async def qdrant_install() -> dict:
    from app import embedded_services
    try:
        return await embedded_services.install()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"install failed: {exc}")


@router.post("/embedded/qdrant/start")
async def qdrant_start() -> dict:
    from app import embedded_services
    try:
        return await embedded_services.start()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc))


@router.post("/embedded/qdrant/stop")
async def qdrant_stop() -> dict:
    from app import embedded_services
    return embedded_services.stop()


# ---------------------------------------------------------------- presets
class Preset(BaseModel):
    name: str
    config: dict


def _presets_path():
    return get_settings().devfoundry_workspace / "presets.json"


def _load() -> dict:
    p = _presets_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


@router.get("/presets")
async def list_presets() -> list[dict]:
    return [{"name": n, "config": c} for n, c in _load().items()]


@router.post("/presets")
async def save_preset(preset: Preset) -> dict:
    data = _load()
    data[preset.name] = preset.config
    _presets_path().write_text(json.dumps(data, indent=2))
    return {"name": preset.name, "saved": True}


@router.delete("/presets/{name}")
async def delete_preset(name: str) -> dict:
    data = _load()
    if name not in data:
        raise HTTPException(404, "preset not found")
    del data[name]
    _presets_path().write_text(json.dumps(data, indent=2))
    return {"name": name, "deleted": True}
