"""Unified LLM client, routed through the provider catalog.

Provider resolution:
1. LLM_PROVIDER set (Models page) -> that provider's endpoint + key
2. LLM_BASE_URL set -> custom OpenAI-compatible gateway
3. ANTHROPIC_API_KEY / OPENAI_API_KEY -> direct fallback

All values are read live from the project .env, so keys saved in Settings
work immediately — no restart needed.
"""
import logging

import httpx

from app.config import env_value

log = logging.getLogger(__name__)


class LLMNotConfigured(RuntimeError):
    pass


def _resolve() -> tuple[str, str, str, str]:
    """-> (kind, base_url, api_key, model)"""
    from app.llm_providers import get_provider, provider_base_url, provider_key

    model = env_value("LLM_MODEL")
    provider_id = env_value("LLM_PROVIDER")
    if provider_id:
        p = get_provider(provider_id)
        if p is None:
            raise LLMNotConfigured(f"unknown LLM_PROVIDER '{provider_id}' — pick one on the Models page")
        base = provider_base_url(p)
        if not base and p["kind"] == "openai":
            raise LLMNotConfigured("custom gateway selected but LLM_BASE_URL is empty")
        return p["kind"], base, provider_key(p), model or p["default_model"]

    if env_value("LLM_BASE_URL"):
        return ("openai", env_value("LLM_BASE_URL").rstrip("/"),
                env_value("LLM_API_KEY") or env_value("OPENAI_API_KEY"), model or "gpt-4o-mini")
    if env_value("ANTHROPIC_API_KEY"):
        return "anthropic", "https://api.anthropic.com/v1", env_value("ANTHROPIC_API_KEY"), model or "claude-sonnet-5"
    if env_value("OPENAI_API_KEY"):
        return "openai", "https://api.openai.com/v1", env_value("OPENAI_API_KEY"), model or "gpt-4o-mini"
    raise LLMNotConfigured(
        "No LLM provider configured. Open the Models page, add a key (or use local Ollama / LM Studio), and pick a model.")


async def complete(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    kind, base, key, model = _resolve()
    if not model:
        raise LLMNotConfigured("No model selected — pick one on the Models page")

    async with httpx.AsyncClient(timeout=300) as client:
        if kind == "anthropic":
            resp = await client.post(
                f"{base}/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": max_tokens,
                      **({"system": system} if system else {}),
                      "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"} if key else {},
            json={"model": model, "max_tokens": max_tokens, "messages": messages},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
