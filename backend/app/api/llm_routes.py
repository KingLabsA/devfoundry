import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import llm_providers
from app.llm import LLMNotConfigured, complete, routing_info

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm")


class TestReq(BaseModel):
    prompt: str = "Reply with exactly: DevFoundry online"
    role: str = ""


@router.get("/providers")
async def providers() -> list[dict]:
    return llm_providers.catalog()


@router.get("/routing")
async def routing() -> dict:
    return await routing_info()


@router.post("/test")
async def test_completion(req: TestReq) -> dict:
    try:
        text = await complete(req.prompt, max_tokens=60, role=req.role)
        return {"ok": True, "response": text[:500]}
    except LLMNotConfigured as exc:
        raise HTTPException(422, str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"LLM call failed: {exc}")


@router.get("/providers/{provider_id}/models")
async def models(provider_id: str) -> dict:
    try:
        found = await llm_providers.list_models(provider_id)
        return {"models": found, "count": len(found)}
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300]
        if exc.response.status_code in (401, 403):
            raise HTTPException(401, f"authentication failed — check the API key ({detail})")
        raise HTTPException(502, f"provider returned {exc.response.status_code}: {detail}")
    except httpx.RequestError as exc:
        raise HTTPException(502, f"cannot reach provider: {exc}")
