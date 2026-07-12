"""Catalog of real LLM providers: 20 cloud APIs + local runtimes + custom gateway.

Every entry is a real, working endpoint. kind="openai" means OpenAI-compatible
/chat/completions and /models; kind="anthropic" uses the Anthropic Messages API.
Local providers (Ollama, LM Studio) need no API key.
"""
import logging
from typing import Any

import httpx

from app.config import env_value

log = logging.getLogger(__name__)

PROVIDERS: list[dict[str, Any]] = [
    {"id": "anthropic", "label": "Anthropic", "kind": "anthropic",
     "base_url": "https://api.anthropic.com/v1", "key_env": "ANTHROPIC_API_KEY",
     "default_model": "claude-sonnet-5", "free": False, "local": False},
    {"id": "openai", "label": "OpenAI", "kind": "openai",
     "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",
     "default_model": "gpt-4o-mini", "free": False, "local": False},
    {"id": "openrouter", "label": "OpenRouter (free models)", "kind": "openai",
     "base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
     "default_model": "openrouter/auto", "free": True, "local": False},
    {"id": "groq", "label": "Groq (free tier)", "kind": "openai",
     "base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY",
     "default_model": "llama-3.3-70b-versatile", "free": True, "local": False},
    {"id": "google", "label": "Google AI Studio (free tier)", "kind": "openai",
     "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "key_env": "GOOGLE_API_KEY",
     "default_model": "gemini-2.0-flash", "free": True, "local": False},
    {"id": "mistral", "label": "Mistral (free tier)", "kind": "openai",
     "base_url": "https://api.mistral.ai/v1", "key_env": "MISTRAL_API_KEY",
     "default_model": "mistral-small-latest", "free": True, "local": False},
    {"id": "cerebras", "label": "Cerebras (free tier)", "kind": "openai",
     "base_url": "https://api.cerebras.ai/v1", "key_env": "CEREBRAS_API_KEY",
     "default_model": "llama-3.3-70b", "free": True, "local": False},
    {"id": "together", "label": "Together AI", "kind": "openai",
     "base_url": "https://api.together.xyz/v1", "key_env": "TOGETHER_API_KEY",
     "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "free": False, "local": False},
    {"id": "deepseek", "label": "DeepSeek", "kind": "openai",
     "base_url": "https://api.deepseek.com/v1", "key_env": "DEEPSEEK_API_KEY",
     "default_model": "deepseek-chat", "free": False, "local": False},
    {"id": "fireworks", "label": "Fireworks AI", "kind": "openai",
     "base_url": "https://api.fireworks.ai/inference/v1", "key_env": "FIREWORKS_API_KEY",
     "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct", "free": False, "local": False},
    {"id": "huggingface", "label": "Hugging Face Inference (free credits)", "kind": "openai",
     "base_url": "https://router.huggingface.co/v1", "key_env": "HF_TOKEN",
     "default_model": "meta-llama/Llama-3.3-70B-Instruct", "free": True, "local": False},
    {"id": "xai", "label": "xAI (Grok)", "kind": "openai",
     "base_url": "https://api.x.ai/v1", "key_env": "XAI_API_KEY",
     "default_model": "grok-3-mini", "free": False, "local": False},
    {"id": "perplexity", "label": "Perplexity", "kind": "openai",
     "base_url": "https://api.perplexity.ai", "key_env": "PERPLEXITY_API_KEY",
     "default_model": "sonar", "free": False, "local": False},
    {"id": "moonshot", "label": "Moonshot (Kimi)", "kind": "openai",
     "base_url": "https://api.moonshot.ai/v1", "key_env": "MOONSHOT_API_KEY",
     "default_model": "kimi-k2-0711-preview", "free": False, "local": False},
    {"id": "zhipu", "label": "Zhipu GLM (free model)", "kind": "openai",
     "base_url": "https://open.bigmodel.cn/api/paas/v4", "key_env": "ZHIPU_API_KEY",
     "default_model": "glm-4-flash", "free": True, "local": False},
    {"id": "dashscope", "label": "Alibaba Qwen (DashScope)", "kind": "openai",
     "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "key_env": "DASHSCOPE_API_KEY",
     "default_model": "qwen-plus", "free": False, "local": False},
    {"id": "nvidia", "label": "NVIDIA NIM (free credits)", "kind": "openai",
     "base_url": "https://integrate.api.nvidia.com/v1", "key_env": "NVIDIA_API_KEY",
     "default_model": "meta/llama-3.3-70b-instruct", "free": True, "local": False},
    {"id": "sambanova", "label": "SambaNova (free tier)", "kind": "openai",
     "base_url": "https://api.sambanova.ai/v1", "key_env": "SAMBANOVA_API_KEY",
     "default_model": "Meta-Llama-3.3-70B-Instruct", "free": True, "local": False},
    {"id": "github", "label": "GitHub Models (free with GitHub)", "kind": "openai",
     "base_url": "https://models.github.ai/inference", "key_env": "GITHUB_TOKEN",
     "default_model": "openai/gpt-4o-mini", "free": True, "local": False},
    {"id": "opencode", "label": "OpenCode Zen (free models, auto-auth from CLI)", "kind": "openai",
     "base_url": "https://opencode.ai/zen/v1", "key_env": "OPENCODE_API_KEY",
     "default_model": "big-pickle", "free": True, "local": False},
    {"id": "freellmapi", "label": "FreeLLMAPI (self-hosted free gateway)", "kind": "openai",
     "base_url": "http://localhost:3002/v1", "key_env": "FREELLMAPI_KEY",
     "default_model": "", "free": True, "local": True},
    {"id": "ollama", "label": "Ollama (local)", "kind": "openai",
     "base_url": "http://localhost:11434/v1", "key_env": "",
     "default_model": "", "free": True, "local": True},
    {"id": "lmstudio", "label": "LM Studio (local)", "kind": "openai",
     "base_url": "http://localhost:1234/v1", "key_env": "",
     "default_model": "", "free": True, "local": True},
    {"id": "custom", "label": "Custom gateway (OpenAI-compatible)", "kind": "openai",
     "base_url": "", "key_env": "LLM_API_KEY",
     "default_model": "", "free": True, "local": True},
]


def get_provider(provider_id: str) -> dict | None:
    return next((p for p in PROVIDERS if p["id"] == provider_id), None)


def _opencode_stored_key() -> str:
    """Reuse the OpenCode CLI's stored auth (~/.local/share/opencode/auth.json) —
    gives keyless access to OpenCode Zen's free models if the user ran `opencode auth login`."""
    import json
    from pathlib import Path

    path = Path.home() / ".local/share/opencode/auth.json"
    try:
        return json.loads(path.read_text()).get("opencode", {}).get("key", "")
    except (OSError, ValueError):
        return ""


def provider_key(p: dict) -> str:
    key = env_value(p["key_env"]) if p["key_env"] else ""
    if not key and p["id"] == "opencode":
        key = _opencode_stored_key()
    return key


def provider_base_url(p: dict) -> str:
    if p["id"] == "custom":
        return env_value("LLM_BASE_URL").rstrip("/")
    override = env_value(f"{p['id'].upper()}_BASE_URL")
    return (override or p["base_url"]).rstrip("/")


def is_configured(p: dict) -> bool:
    if p["id"] == "custom":
        return bool(env_value("LLM_BASE_URL"))
    return p["local"] or bool(provider_key(p))


def catalog() -> list[dict]:
    active = env_value("LLM_PROVIDER")
    return [{
        "id": p["id"], "label": p["label"], "kind": p["kind"], "free": p["free"],
        "local": p["local"], "base_url": provider_base_url(p), "key_env": p["key_env"],
        "default_model": p["default_model"], "configured": is_configured(p),
        "active": p["id"] == active,
    } for p in PROVIDERS]


async def list_models(provider_id: str) -> list[str]:
    """Test connectivity and return real model ids from the provider."""
    p = get_provider(provider_id)
    if p is None:
        raise ValueError(f"unknown provider: {provider_id}")
    base = provider_base_url(p)
    if not base:
        raise ValueError("no base URL configured — set the gateway URL in Settings")
    key = provider_key(p)
    if p["kind"] == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    else:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{base}/models", headers=headers)
        resp.raise_for_status()
        data = resp.json()
    items = data.get("data", data.get("models", []))
    models = [m.get("id") or m.get("name", "") for m in items if isinstance(m, dict)]
    return sorted(m for m in models if m)
