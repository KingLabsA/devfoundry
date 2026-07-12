import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import RunCreated, RunRequest, RunState
from app.orchestrator.pipeline import orchestrator

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/runs", response_model=RunCreated, status_code=202)
async def create_run(req: RunRequest) -> RunCreated:
    state = orchestrator.start_run(req.idea.strip())
    log.info("Started run %s", state.run_id)
    return RunCreated(run_id=state.run_id)


@router.get("/runs", response_model=list[RunState])
async def list_runs() -> list[RunState]:
    return list(orchestrator.runs.values())


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
