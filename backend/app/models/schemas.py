from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Stage(str, Enum):
    QUEUED = "queued"
    SPEC = "spec"            # MetaGPT: PRD, architecture, API specs
    CODEGEN = "codegen"      # Bolt.diy: full codebase
    TASKS = "tasks"          # Orc: task breakdown / allocation
    REFINE = "refine"        # OpenCode: iterative fixes
    DEPLOY = "deploy"        # Superpowers: package + deploy
    DONE = "done"
    FAILED = "failed"


class RunRequest(BaseModel):
    idea: str = Field(..., min_length=10, max_length=4000)
    deploy_target: str = ""      # override DEPLOY_TARGET for this run
    custom_domain: str = ""      # e.g. myapp.surge.sh / netlify site name
    skills: list[str] = Field(default_factory=list)  # design/capability skills
    reasoning: str = ""  # fast | balanced | deep | ensemble | auto ("" = env default)


class RunCreated(BaseModel):
    run_id: str


class DeployRequest(BaseModel):
    deploy_target: str = ""
    custom_domain: str = ""


class PipelineEvent(BaseModel):
    run_id: str
    stage: Stage
    kind: str                # "log" | "artifact" | "status" | "error"
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunState(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    idea: str
    stage: Stage = Stage.QUEUED
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
