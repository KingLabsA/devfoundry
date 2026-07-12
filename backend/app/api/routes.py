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


@router.get("/runs/{run_id}", response_model=RunState)
async def get_run(run_id: str) -> RunState:
    state = orchestrator.runs.get(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    return state


@router.get("/health")
async def health() -> dict:
    return {
        "backend": "ok",
        "metagpt": await orchestrator.metagpt.health(),
        "boltdiy": await orchestrator.boltdiy.health(),
        "opencode": await orchestrator.opencode.health(),
        "orc": await orchestrator.orc.health(),
        "superpowers": await orchestrator.superpowers.health(),
    }
