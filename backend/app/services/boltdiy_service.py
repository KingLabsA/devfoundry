from typing import Any

from app.models.schemas import Stage
from app.services.base import FrameworkService


class BoltDiyService(FrameworkService):
    """Generates a complete application codebase from the MetaGPT specs."""

    name = "boltdiy"
    stage = Stage.CODEGEN

    async def generate_codebase(self, run_id: str, idea: str, specs: dict[str, Any]) -> dict[str, Any]:
        await self._emit(run_id, "Bolt.diy: generating full application codebase...")
        result = await self._post("/api/generate", {
            "prompt": idea,
            "context": {"prd": specs.get("prd", ""), "architecture": specs.get("architecture", ""),
                        "api_spec": specs.get("api_spec", "")},
        })
        files = result.get("files", {})
        await self._emit(run_id, f"Bolt.diy generated {len(files)} files", kind="artifact",
                         artifact="codebase_manifest", files=sorted(files.keys()))
        return {"files": files, "project_dir": result.get("project_dir", "")}
