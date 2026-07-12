"""Spec service: multi-role (PM / Architect / API designer) document generation.

Uses the real MetaGPT company simulation when the library is installed
(USE_METAGPT=1 image variant); otherwise runs role-prompted LLM calls that
produce the same three artifacts. Either way the contract is identical.
"""
import asyncio
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llm import LLMNotConfigured, complete

logging.basicConfig(level="INFO")
log = logging.getLogger("metagpt-service")
app = FastAPI()

try:
    from metagpt.software_company import generate_repo  # type: ignore
    HAS_METAGPT = True
except ImportError:
    HAS_METAGPT = False
    log.info("metagpt library not installed — using role-prompted LLM spec generation")


class RunReq(BaseModel):
    idea: str
    investment: float = 3.0
    n_round: int = 5


@app.get("/health")
def health():
    return {"ok": True, "engine": "metagpt" if HAS_METAGPT else "llm-roles"}


async def _llm_specs(idea: str) -> dict:
    pm = "You are a senior Product Manager at a software company."
    architect = "You are a principal Software Architect."
    api = "You are an API designer. Output an OpenAPI-style spec in markdown."
    prd, arch, spec = await asyncio.gather(
        complete(f"Write a concise PRD (goals, users, core features, success metrics) for: {idea}", pm),
        complete(f"Design the system architecture (components, data flow, stack choices, one ASCII diagram) for: {idea}", architect),
        complete(f"Define the REST API (resources, endpoints, request/response schemas) for: {idea}", api),
    )
    return {"prd": prd, "architecture": arch, "api_spec": spec}


@app.post("/v1/company/run")
async def run(req: RunReq):
    try:
        if HAS_METAGPT:
            repo = await asyncio.to_thread(generate_repo, req.idea)
            docs = {d.filename: d.content for d in repo.docs.get_all()} if hasattr(repo, "docs") else {}
            return {
                "prd": docs.get("prd.md", ""),
                "architecture": docs.get("system_design.md", ""),
                "api_spec": docs.get("api_spec.md", ""),
            }
        return await _llm_specs(req.idea)
    except LLMNotConfigured as exc:
        raise HTTPException(500, str(exc))
    except Exception as exc:
        log.exception("spec generation failed")
        raise HTTPException(500, str(exc))
