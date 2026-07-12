"""Orc adapter: feature decomposition + task board with AI-developer assignment."""
import json
import logging
import os
import re
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level="INFO")
app = FastAPI()
TASKS: dict[str, dict] = {}
DEVELOPERS = ["ai-dev-1", "ai-dev-2", "ai-dev-3"]


class PlanReq(BaseModel):
    prd: str
    files: list[str] = []


class CompleteReq(BaseModel):
    task_id: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/plan")
async def plan(req: PlanReq):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not set")
    prompt = (
        "Break this PRD into 3-8 concrete development tasks. "
        "Return JSON array of {title, description}.\n\nPRD:\n" + req.prd[:8000]
        + "\n\nExisting files:\n" + "\n".join(req.files[:200])
    )
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-5", "max_tokens": 4000,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
    text = resp.json()["content"][0]["text"]
    match = re.search(r"\[[\s\S]*\]", text)
    raw = json.loads(match.group(0)) if match else []
    tasks = []
    for i, t in enumerate(raw):
        task = {"id": uuid.uuid4().hex[:8], "title": t.get("title", f"Task {i+1}"),
                "description": t.get("description", ""), "assignee": DEVELOPERS[i % len(DEVELOPERS)],
                "status": "todo"}
        TASKS[task["id"]] = task
        tasks.append(task)
    return {"tasks": tasks}


@app.post("/api/tasks/complete")
def complete(req: CompleteReq):
    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(404, "task not found")
    task["status"] = "done"
    return task
