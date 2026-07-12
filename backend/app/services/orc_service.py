from typing import Any

from app.models.schemas import Stage
from app.services.base import FrameworkService


class OrcService(FrameworkService):
    """Breaks features into tasks and assigns them to AI developer agents."""

    name = "orc"
    stage = Stage.TASKS

    async def plan_tasks(self, run_id: str, specs: dict[str, Any], codebase: dict[str, Any]) -> list[dict[str, Any]]:
        await self._emit(run_id, "Orc: decomposing features into developer tasks...")
        result = await self._post("/api/plan", {
            "prd": specs.get("prd", ""),
            "files": list(codebase.get("files", {}).keys()),
        })
        tasks = result.get("tasks", [])
        await self._emit(run_id, f"Orc created {len(tasks)} tasks", kind="artifact", artifact="task_board", tasks=tasks)
        return tasks

    async def mark_done(self, run_id: str, task_id: str) -> None:
        await self._post("/api/tasks/complete", {"task_id": task_id})
        await self._emit(run_id, f"Orc: task {task_id} completed", kind="status", task_id=task_id)
