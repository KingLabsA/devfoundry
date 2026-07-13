import asyncio
import json
import logging
from pathlib import Path

from app.config import get_settings
from app.events.bus import bus
from app.models.schemas import PipelineEvent, RunState, Stage
from app.services.base import ServiceError
from app.services.boltdiy_service import BoltDiyService
from app.services.metagpt_service import MetaGPTService
from app.services.opencode_service import OpenCodeService
from app.services.orc_service import OrcService
from app.services.superpowers_service import SuperpowersService

log = logging.getLogger(__name__)

MAX_REFINE_ITERATIONS = 3


class Orchestrator:
    def __init__(self) -> None:
        s = get_settings()
        self.metagpt = MetaGPTService(s.metagpt_url)
        self.boltdiy = BoltDiyService(s.boltdiy_url)
        self.opencode = OpenCodeService(s.opencode_url)
        self.orc = OrcService(s.orc_url)
        self.superpowers = SuperpowersService(s.superpowers_url)
        self.runs: dict[str, RunState] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def start_run(self, idea: str, deploy_target: str = "", custom_domain: str = "") -> RunState:
        state = RunState(idea=idea)
        if deploy_target or custom_domain:
            state.artifacts["deploy_config"] = {"target": deploy_target, "domain": custom_domain}
        self.runs[state.run_id] = state
        self._persist(state)
        self._tasks[state.run_id] = asyncio.create_task(self._execute(state))
        return state

    @staticmethod
    def _persist(state: RunState) -> None:
        try:
            from app import store
            store.save_run(state)
        except Exception:  # noqa: BLE001 — never let persistence break a run
            log.exception("failed to persist run %s", state.run_id)

    def load_history(self) -> None:
        """Rehydrate past runs from SQLite so they appear after a restart."""
        try:
            from app import store
            from app.models.schemas import Stage as _Stage
            for row in store.list_runs():
                if row["run_id"] in self.runs:
                    continue
                self.runs[row["run_id"]] = RunState(
                    run_id=row["run_id"], idea=row["idea"],
                    stage=_Stage(row["stage"]), artifacts=row["artifacts"], error=row["error"])
            log.info("loaded %d past runs from history", len(self.runs))
        except Exception:  # noqa: BLE001
            log.exception("failed to load run history")

    async def stop_run(self, run_id: str) -> bool:
        task = self._tasks.get(run_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def _set_stage(self, state: RunState, stage: Stage, message: str) -> None:
        state.stage = stage
        self._persist(state)
        await bus.publish(PipelineEvent(run_id=state.run_id, stage=stage, kind="status", message=message))

    async def _execute(self, state: RunState) -> None:
        run_id = state.run_id
        settings = get_settings()
        workspace = settings.devfoundry_workspace / run_id
        workspace.mkdir(parents=True, exist_ok=True)
        if settings.devfoundry_mock:
            from app.orchestrator.mock import run_mock_pipeline
            try:
                await run_mock_pipeline(state, self._set_stage)
            except Exception as exc:  # noqa: BLE001
                state.error = str(exc)
                await self._set_stage(state, Stage.FAILED, f"Demo pipeline error: {exc}")
            return
        if settings.devfoundry_embedded:
            from app.orchestrator.embedded import run_embedded_pipeline
            try:
                await run_embedded_pipeline(state, self._set_stage, workspace)
            except asyncio.CancelledError:
                state.error = "stopped by user"
                await asyncio.shield(self._set_stage(state, Stage.FAILED, "Run stopped by user"))
            except Exception as exc:  # noqa: BLE001
                state.error = str(exc)
                log.exception("Embedded run %s failed", run_id)
                await self._set_stage(state, Stage.FAILED, f"Pipeline failed: {exc}")
            return
        try:
            # 1. MetaGPT — PRD, architecture, API specs
            await self._set_stage(state, Stage.SPEC, "Generating specifications with MetaGPT")
            specs = await self.metagpt.generate_specs(run_id, state.idea)
            state.artifacts["specs"] = specs
            self._save(workspace / "specs.json", specs)

            # 2. Bolt.diy — full codebase
            await self._set_stage(state, Stage.CODEGEN, "Generating codebase with Bolt.diy")
            codebase = await self.boltdiy.generate_codebase(run_id, state.idea, specs)
            project_dir = codebase.get("project_dir") or str(workspace / "app")
            self._materialize(Path(project_dir), codebase.get("files", {}))
            state.artifacts["project_dir"] = project_dir

            # 3. Orc — task breakdown + allocation
            await self._set_stage(state, Stage.TASKS, "Planning tasks with Orc")
            tasks = await self.orc.plan_tasks(run_id, specs, codebase)
            state.artifacts["tasks"] = tasks

            # 4. OpenCode — implement tasks, then iterate until tests pass
            await self._set_stage(state, Stage.REFINE, "Refining code with OpenCode")
            for task in tasks:
                await self.opencode.execute_task(run_id, project_dir, task)
                if task.get("id"):
                    await self.orc.mark_done(run_id, task["id"])

            for i in range(MAX_REFINE_ITERATIONS):
                results = await self.opencode.run_tests(run_id, project_dir)
                if results.get("failed", 0) == 0:
                    break
                await self.opencode.execute_task(run_id, project_dir, {
                    "title": f"Fix failing tests (iteration {i + 1})",
                    "description": f"Fix these test failures:\n{results.get('failures', '')}",
                })
            else:
                await bus.publish(PipelineEvent(
                    run_id=run_id, stage=Stage.REFINE, kind="log",
                    message=f"Tests still failing after {MAX_REFINE_ITERATIONS} iterations; proceeding to deploy"))

            # 5. Superpowers — package + deploy
            await self._set_stage(state, Stage.DEPLOY, "Deploying with Superpowers")
            deployment = await self.superpowers.deploy(run_id, project_dir)
            state.artifacts["deployment"] = deployment

            await self._set_stage(state, Stage.DONE, "Pipeline complete")
        except ServiceError as exc:
            state.error = str(exc)
            log.exception("Run %s failed", run_id)
            await self._set_stage(state, Stage.FAILED, f"Pipeline failed: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            state.error = str(exc)
            log.exception("Run %s crashed", run_id)
            await self._set_stage(state, Stage.FAILED, f"Unexpected error: {exc}")

    @staticmethod
    def _save(path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, default=str))

    @staticmethod
    def _materialize(root: Path, files: dict[str, str]) -> None:
        for rel, content in files.items():
            target = (root / rel).resolve()
            if not str(target).startswith(str(root.resolve())):
                log.warning("Skipping path-traversal file entry: %s", rel)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)


orchestrator = Orchestrator()
