import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import DeployRequest, RunCreated, RunRequest, RunState
from app.orchestrator.pipeline import orchestrator

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/runs", response_model=RunCreated, status_code=202)
async def create_run(req: RunRequest) -> RunCreated:
    state = orchestrator.start_run(
        req.idea.strip(), deploy_target=req.deploy_target,
        custom_domain=req.custom_domain, skills=req.skills)
    log.info("Started run %s", state.run_id)
    return RunCreated(run_id=state.run_id)


@router.get("/runs")
async def list_runs() -> list[dict]:
    from app import store
    persisted = {r["run_id"]: r for r in store.list_runs()}
    # overlay in-memory (fresher) state
    for rid, state in orchestrator.runs.items():
        persisted[rid] = {"run_id": rid, "idea": state.idea, "stage": state.stage.value,
                          "error": state.error, "artifacts": state.artifacts,
                          "created_at": persisted.get(rid, {}).get("created_at", ""),
                          "updated_at": persisted.get(rid, {}).get("updated_at", "")}
    return sorted(persisted.values(), key=lambda r: r.get("created_at", ""), reverse=True)


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str) -> list[dict]:
    from app import store
    return store.get_events(run_id)


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str) -> dict:
    from app import store
    orchestrator.runs.pop(run_id, None)
    removed = store.delete_run(run_id)
    return {"run_id": run_id, "deleted": removed}


@router.post("/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict:
    if run_id not in orchestrator.runs:
        raise HTTPException(404, "run not found")
    stopped = await orchestrator.stop_run(run_id)
    return {"run_id": run_id, "stopped": stopped}


@router.post("/runs/{run_id}/redeploy")
async def redeploy(run_id: str, req: DeployRequest | None = None) -> dict:
    """Re-run only the deploy stage for a finished run, honoring a new target/domain."""
    state = orchestrator.runs.get(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    from pathlib import Path

    from app.config import get_settings
    from app.models.schemas import Stage
    from app.orchestrator.embedded import deploy_stage

    workspace = get_settings().devfoundry_workspace / run_id
    # prefer the generated project dir; fall back to the run root (uploaded/edited files)
    project_dir = state.artifacts.get("project_dir")
    if not project_dir or not Path(project_dir).is_dir():
        app_dir = workspace / "app"
        project_dir = str(app_dir if app_dir.is_dir() else workspace)
    if not Path(project_dir).is_dir():
        raise HTTPException(409, "run has no files to deploy")
    cfg = {"target": (req.deploy_target if req else ""), "domain": (req.custom_domain if req else "")}
    await orchestrator._set_stage(state, Stage.DEPLOY, "Re-deploying")
    result = await deploy_stage(run_id, Path(project_dir), workspace, cfg)
    state.artifacts["deployment"] = result
    await orchestrator._set_stage(state, Stage.DONE, "Re-deploy complete")
    return result


@router.get("/runs/{run_id}", response_model=RunState)
async def get_run(run_id: str) -> RunState:
    state = orchestrator.runs.get(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    return state


@router.get("/health")
async def health() -> dict:
    from app.config import get_settings

    settings = get_settings()
    if settings.devfoundry_mock or settings.devfoundry_embedded:
        mode = "mock" if settings.devfoundry_mock else "embedded"
        return {"backend": "ok", "mode": mode, "metagpt": True, "boltdiy": True,
                "opencode": True, "orc": True, "superpowers": True}
    return {
        "backend": "ok",
        "mode": "isolated",
        "metagpt": await orchestrator.metagpt.health(),
        "boltdiy": await orchestrator.boltdiy.health(),
        "opencode": await orchestrator.opencode.health(),
        "orc": await orchestrator.orc.health(),
        "superpowers": await orchestrator.superpowers.health(),
    }
