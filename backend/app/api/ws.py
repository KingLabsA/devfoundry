import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.events.bus import bus

log = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def run_stream(ws: WebSocket, run_id: str) -> None:
    await ws.accept()
    queue, replay = await bus.subscribe(run_id)
    try:
        for event in replay:
            await ws.send_text(event.model_dump_json())
        while True:
            event = await queue.get()
            await ws.send_text(event.model_dump_json())
            if event.kind == "status" and event.stage in ("done", "failed"):
                break
    except WebSocketDisconnect:
        log.info("WebSocket client left run %s", run_id)
    except Exception:
        log.exception("WebSocket error on run %s", run_id)
    finally:
        await bus.unsubscribe(run_id, queue)
        await asyncio.shield(_close(ws))


async def _close(ws: WebSocket) -> None:
    try:
        await ws.close()
    except RuntimeError:
        pass
