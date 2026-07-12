"""Unified LLM client: Anthropic native, or any OpenAI-compatible gateway.

Provider resolution order:
1. LLM_BASE_URL set  -> OpenAI-compatible /chat/completions (key: LLM_API_KEY or OPENAI_API_KEY)
2. ANTHROPIC_API_KEY -> Anthropic Messages API
3. OPENAI_API_KEY    -> api.openai.com
"""
import logging
import os

import httpx

log = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class LLMNotConfigured(RuntimeError):
    pass


async def complete(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    model = os.environ.get("LLM_MODEL", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    async with httpx.AsyncClient(timeout=300) as client:
        if base_url or (openai_key and not anthropic_key):
            url = f"{base_url or 'https://api.openai.com/v1'}/chat/completions"
            messages = ([{"role": "system", "content": system}] if system else []) + [
                {"role": "user", "content": prompt}
            ]
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {openai_key}"} if openai_key else {},
                json={"model": model or DEFAULT_OPENAI_MODEL, "max_tokens": max_tokens, "messages": messages},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        if anthropic_key:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01"},
                json={
                    "model": model or DEFAULT_ANTHROPIC_MODEL,
                    "max_tokens": max_tokens,
                    **({"system": system} if system else {}),
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

    raise LLMNotConfigured(
        "No LLM provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or LLM_BASE_URL in Settings."
    )
