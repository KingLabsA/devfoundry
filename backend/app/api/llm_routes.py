import logging

import httpx
from fastapi import APIRouter, HTTPException

from app import llm_providers

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm")


@router.get("/providers")
async def providers() -> list[dict]:
    return llm_providers.catalog()


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
