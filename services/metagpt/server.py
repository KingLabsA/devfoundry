import asyncio
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level="INFO")
app = FastAPI()


class RunReq(BaseModel):
    idea: str
    investment: float = 3.0
    n_round: int = 5


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/company/run")
async def run(req: RunReq):
    from metagpt.software_company import generate_repo
    try:
        repo = await asyncio.to_thread(generate_repo, req.idea)
        docs = {d.filename: d.content for d in repo.docs.get_all()} if hasattr(repo, "docs") else {}
        return {
            "prd": docs.get("prd.md", ""),
            "architecture": docs.get("system_design.md", ""),
            "api_spec": docs.get("api_spec.md", ""),
        }
    except Exception as exc:
        logging.exception("MetaGPT run failed")
        raise HTTPException(500, str(exc))
