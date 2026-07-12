from typing import Any

from app.models.schemas import Stage
from app.services.base import FrameworkService


class MetaGPTService(FrameworkService):
    """Simulates a software company (PM, Architect, Dev, QA) to produce PRD,
    architecture docs, and API specs from a natural-language idea."""

    name = "metagpt"
    stage = Stage.SPEC

    async def generate_specs(self, run_id: str, idea: str) -> dict[str, Any]:
        await self._emit(run_id, "MetaGPT: assembling virtual team (PM, Architect, Dev, QA)...")
        result = await self._post("/v1/company/run", {"idea": idea, "investment": 3.0, "n_round": 5})
        specs = {
            "prd": result.get("prd", ""),
            "architecture": result.get("architecture", ""),
            "api_spec": result.get("api_spec", ""),
        }
        for name, doc in specs.items():
            if doc:
                await self._emit(run_id, f"MetaGPT produced {name}", kind="artifact", artifact=name, content=doc)
        return specs
