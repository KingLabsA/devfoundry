from typing import Any

from app.models.schemas import Stage
from app.services.base import FrameworkService


class OpenCodeService(FrameworkService):
    """Iteratively refines the generated code: implements tasks, fixes bugs,
    and maintains core business logic."""

    name = "opencode"
    stage = Stage.REFINE

    async def execute_task(self, run_id: str, project_dir: str, task: dict[str, Any]) -> dict[str, Any]:
        title = task.get("title", task.get("id", "task"))
        await self._emit(run_id, f"OpenCode: working on '{title}'...")
        result = await self._post("/api/run", {
            "project_dir": project_dir,
            "instruction": task.get("description", title),
        })
        changed = result.get("changed_files", [])
        await self._emit(run_id, f"OpenCode changed {len(changed)} files for '{title}'",
                         kind="artifact", artifact="diff", task=title, changed_files=changed,
                         summary=result.get("summary", ""))
        return result

    async def run_tests(self, run_id: str, project_dir: str) -> dict[str, Any]:
        await self._emit(run_id, "OpenCode: running test suite...")
        result = await self._post("/api/test", {"project_dir": project_dir})
        await self._emit(run_id, f"Tests: {result.get('passed', 0)} passed, {result.get('failed', 0)} failed",
                         kind="status", **result)
        return result
