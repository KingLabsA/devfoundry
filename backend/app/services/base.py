import logging
from typing import Any

import httpx

from app.config import get_settings
from app.events.bus import bus
from app.models.schemas import PipelineEvent, Stage

log = logging.getLogger(__name__)


class ServiceError(RuntimeError):
    pass


class FrameworkService:
    """Base HTTP client for an isolated framework sidecar service."""

    name: str = "base"
    stage: Stage = Stage.QUEUED

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = get_settings().service_timeout_seconds

    async def _emit(self, run_id: str, message: str, kind: str = "log", **payload: Any) -> None:
        await bus.publish(PipelineEvent(run_id=run_id, stage=self.stage, kind=kind, message=message, payload=payload))

    async def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=json)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            log.error("%s returned %s: %s", url, exc.response.status_code, exc.response.text[:500])
            raise ServiceError(f"{self.name}: HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            log.error("%s unreachable: %s", url, exc)
            raise ServiceError(f"{self.name}: service unreachable at {self.base_url}") from exc

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except httpx.RequestError:
            return False
