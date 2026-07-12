"""Codegen service (bolt.diy-style): full application codebase from specs.

Prompts the configured LLM to emit a complete file map as JSON, in one shot,
grounded in the PRD / architecture / API spec produced by the spec stage.
"""
import json
import logging
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llm import LLMNotConfigured, complete

logging.basicConfig(level="INFO")
log = logging.getLogger("codegen-service")
app = FastAPI()

SYSTEM = (
    "You are an expert full-stack engineer. Generate a complete, runnable application. "
    "Respond with ONLY a JSON object: {\"files\": {\"relative/path\": \"file content\", ...}}. "
    "Include a package manifest, entrypoint, README, and at least one test. "
    "No markdown fences, no commentary — raw JSON only."
)


class GenReq(BaseModel):
    prompt: str
    context: dict = {}


@app.get("/health")
def health():
    return {"ok": True, "engine": "llm-codegen"}


def _extract_files(text: str) -> dict[str, str]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("model returned no JSON object")
    data = json.loads(match.group(0))
    files = data.get("files", data)
    if not isinstance(files, dict) or not files:
        raise ValueError("no files in model response")
    return {str(k): str(v) for k, v in files.items()}


@app.post("/api/generate")
async def generate(req: GenReq):
    ctx = req.context or {}
    prompt = (
        f"Build this application: {req.prompt}\n\n"
        f"## PRD\n{ctx.get('prd', '')[:6000]}\n\n"
        f"## Architecture\n{ctx.get('architecture', '')[:4000]}\n\n"
        f"## API Spec\n{ctx.get('api_spec', '')[:4000]}"
    )
    try:
        text = await complete(prompt, SYSTEM, max_tokens=16000)
        files = _extract_files(text)
        log.info("generated %d files", len(files))
        return {"files": files, "project_dir": ""}
    except LLMNotConfigured as exc:
        raise HTTPException(500, str(exc))
    except (ValueError, json.JSONDecodeError) as exc:
        log.error("unparseable model output: %s", exc)
        raise HTTPException(502, f"codegen output not parseable: {exc}")
    except Exception as exc:
        log.exception("codegen failed")
        raise HTTPException(500, str(exc))
