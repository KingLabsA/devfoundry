from typing import Any

from app.models.schemas import Stage
from app.services.base import FrameworkService


class SuperpowersService(FrameworkService):
    """Orchestrates final packaging and deployment of the built application."""

    name = "superpowers"
    stage = Stage.DEPLOY

    async def deploy(self, run_id: str, project_dir: str) -> dict[str, Any]:
        await self._emit(run_id, "Superpowers: packaging application...")
        result = await self._post("/api/deploy", {"project_dir": project_dir, "target": "container"})
        await self._emit(run_id, "Superpowers: deployment complete", kind="artifact",
                         artifact="deployment", url=result.get("url", ""), logs=result.get("logs", ""))
        return result
