"""Demo pipeline: emits a realistic scripted run with no external services.

Enabled with DEVFOUNDRY_MOCK=1 — used for demos, tutorials, and UI development.
"""
import asyncio

from app.events.bus import bus
from app.models.schemas import PipelineEvent, RunState, Stage

_PRD = """# PRD — {idea}

## Goal
{idea}

## Users
- Primary: end users who need this daily
- Secondary: admins configuring the workspace

## Core Features
1. Onboarding & auth
2. Main workflow (create, track, review)
3. Notifications
4. Admin dashboard

## Success Metrics
- Weekly active usage > 40%
- Task completion < 3 clicks
"""

_ARCH = """# Architecture

- **Frontend**: React SPA
- **API**: FastAPI, JWT auth
- **DB**: Postgres
- **Jobs**: background worker + queue

```
client -> api -> service layer -> repository -> postgres
                     \\-> queue -> worker
```
"""

_TASKS = [
    {"id": "t1", "title": "Scaffold API and data model", "assignee": "ai-dev-1", "status": "todo"},
    {"id": "t2", "title": "Implement core workflow endpoints", "assignee": "ai-dev-2", "status": "todo"},
    {"id": "t3", "title": "Build frontend views", "assignee": "ai-dev-3", "status": "todo"},
    {"id": "t4", "title": "Add notifications + tests", "assignee": "ai-dev-1", "status": "todo"},
]

_FILES = ["src/main.py", "src/models.py", "src/api/routes.py", "web/src/App.tsx", "tests/test_api.py"]


async def run_mock_pipeline(state: RunState, set_stage) -> None:
    run_id = state.run_id

    async def emit(stage: Stage, message: str, kind: str = "log", **payload):
        await bus.publish(PipelineEvent(run_id=run_id, stage=stage, kind=kind, message=message, payload=payload))
        await asyncio.sleep(0.6)

    await set_stage(state, Stage.SPEC, "Generating specifications with MetaGPT (demo)")
    await emit(Stage.SPEC, "MetaGPT: assembling virtual team (PM, Architect, Dev, QA)...")
    await emit(Stage.SPEC, "PM drafted the product requirements")
    await emit(Stage.SPEC, "MetaGPT produced prd", kind="artifact", artifact="prd",
               content=_PRD.format(idea=state.idea))
    await emit(Stage.SPEC, "MetaGPT produced architecture", kind="artifact", artifact="architecture", content=_ARCH)
    state.artifacts["specs"] = {"prd": _PRD.format(idea=state.idea), "architecture": _ARCH}

    await set_stage(state, Stage.CODEGEN, "Generating codebase with Bolt.diy (demo)")
    for f in _FILES:
        await emit(Stage.CODEGEN, f"Bolt.diy wrote {f}")
    await emit(Stage.CODEGEN, f"Bolt.diy generated {len(_FILES)} files", kind="artifact",
               artifact="codebase_manifest", files=_FILES)

    await set_stage(state, Stage.TASKS, "Planning tasks with Orc (demo)")
    await emit(Stage.TASKS, f"Orc created {len(_TASKS)} tasks", kind="artifact", artifact="task_board", tasks=_TASKS)
    state.artifacts["tasks"] = _TASKS

    await set_stage(state, Stage.REFINE, "Refining code with OpenCode (demo)")
    for t in _TASKS:
        await emit(Stage.REFINE, f"OpenCode: working on '{t['title']}'...")
        await emit(Stage.REFINE, f"OpenCode changed 3 files for '{t['title']}'", kind="artifact",
                   artifact="diff", task=t["title"], changed_files=_FILES[:3])
    await emit(Stage.REFINE, "Tests: 12 passed, 0 failed", kind="status", passed=12, failed=0)

    await set_stage(state, Stage.DEPLOY, "Packaging & deploying with Superpowers (demo)")
    await emit(Stage.DEPLOY, "Superpowers: building container image...")
    await emit(Stage.DEPLOY, "Superpowers: deployment complete", kind="artifact", artifact="deployment",
               url="http://localhost:3000", logs="image built: demo-app:latest")
    state.artifacts["deployment"] = {"url": "http://localhost:3000"}

    await set_stage(state, Stage.DONE, "Pipeline complete (demo mode)")
