"""Local-hardware LLM recommendations + smart auto-router across connected providers."""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app import llm_providers

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class Specs(BaseModel):
    ram_gb: int = 0
    cpu_cores: int = 0
    arch: str = ""
    chip: str = ""
    gpu: str = ""


# Curated local models keyed by the RAM they comfortably fit (Q4 quantized).
# Each: (ollama tag, hugging-face repo, params, min RAM GB).
_LOCAL_MODELS = [
    ("qwen2.5-coder:1.5b", "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF", "1.5B coder", 4),
    ("llama3.2:3b", "bartowski/Llama-3.2-3B-Instruct-GGUF", "3B general", 6),
    ("qwen2.5-coder:7b", "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "7B coder", 8),
    ("llama3.1:8b", "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "8B general", 8),
    ("deepseek-coder-v2:16b", "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF", "16B MoE coder", 16),
    ("qwen2.5-coder:14b", "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF", "14B coder", 16),
    ("qwen2.5:32b", "bartowski/Qwen2.5-32B-Instruct-GGUF", "32B general", 32),
    ("qwen2.5-coder:32b", "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF", "32B coder (best local)", 32),
]


@router.post("/hardware/recommend")
async def recommend(specs: Specs) -> dict:
    ram = specs.ram_gb or 8
    # leave ~6GB headroom for the OS/app; Apple unified memory shares with the GPU
    budget = max(4, ram - 6)
    fits = [{"ollama": t, "hf": hf, "label": lbl, "min_ram": mr}
            for (t, hf, lbl, mr) in _LOCAL_MODELS if mr <= budget]
    best = fits[-1] if fits else None
    tier = ("high-end" if ram >= 32 else "capable" if ram >= 16 else "modest" if ram >= 8 else "low")
    metal = "metal" in (specs.gpu or "").lower() or specs.arch in ("aarch64", "arm64")
    return {
        "specs": specs.model_dump(),
        "tier": tier,
        "metal": metal,
        "recommended": best,
        "options": fits[-5:][::-1],
        "note": (f"Your machine ({ram}GB, {specs.chip or specs.arch}) comfortably runs "
                 f"models up to ~{budget}GB (Q4). "
                 + ("Apple Metal accelerates inference via Ollama/MLX." if metal else "")),
    }


@router.get("/router/providers")
async def router_providers() -> dict:
    """All providers with connection + free/paid status, and a suggested rotation
    built from every connected free provider (the 'auto-router')."""
    cat = llm_providers.catalog()
    connected = [p for p in cat if p["configured"]]
    free_connected = [p for p in connected if p["free"]]
    paid_connected = [p for p in connected if not p["free"]]
    rotation = [f'{p["id"]}:{p["default_model"]}' for p in free_connected if p["default_model"]]
    return {
        "total": len(cat),
        "connected": len(connected),
        "free_connected": [p["id"] for p in free_connected],
        "paid_connected": [p["id"] for p in paid_connected],
        "suggested_rotation": rotation,
    }
