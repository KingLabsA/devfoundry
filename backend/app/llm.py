"""Unified LLM client with MoE stage routing, rotation/failover, and local auto-detect.

Candidate order for each call:
1. Stage expert (MoE): LLM_MODEL_<ROLE> (e.g. LLM_MODEL_CODEGEN="ollama:qwen2.5-coder")
2. Active selection:   LLM_PROVIDER + LLM_MODEL (Models page)
3. Rotation list:      LLM_ROTATION="groq:llama-3.3-70b-versatile, openrouter:openrouter/auto"
4. Legacy fallbacks:   LLM_BASE_URL / ANTHROPIC_API_KEY / OPENAI_API_KEY
5. Auto-detect:        running local runtimes — FreeLLMAPI (:3002), Ollama (:11434), LM Studio (:1234)

Candidates are tried in order; retryable failures (429, 5xx, timeouts, unreachable)
rotate to the next candidate. All config is read live from .env — no restart needed.
Model strings may be "provider:model" or bare "model" (uses the active provider).
"""
import logging
import time

import httpx

from app.config import env_value

log = logging.getLogger(__name__)

_LOCAL_PROBE_ORDER = ("freellmapi", "ollama", "lmstudio")
_detect_cache: dict = {"ts": 0.0, "result": None}


class LLMNotConfigured(RuntimeError):
    pass


def _endpoint(provider_id: str) -> tuple[str, str, str] | None:
    """provider id -> (kind, base_url, key), or None if unusable."""
    from app.llm_providers import get_provider, provider_base_url, provider_key

    p = get_provider(provider_id)
    if p is None:
        return None
    base = provider_base_url(p)
    if not base:
        return None
    return p["kind"], base, provider_key(p)


def _parse_model_ref(ref: str, default_provider: str) -> tuple[str, str] | None:
    """'provider:model' or bare 'model' -> (provider_id, model)."""
    from app.llm_providers import get_provider

    ref = ref.strip()
    if not ref:
        return None
    if ":" in ref:
        prefix, rest = ref.split(":", 1)
        if get_provider(prefix.strip()):
            return prefix.strip(), rest.strip()
    if default_provider:
        return default_provider, ref
    return None


async def _autodetect() -> tuple[str, str] | None:
    """Find a running local runtime and its first model. Cached for 60s."""
    if time.time() - _detect_cache["ts"] < 60:
        return _detect_cache["result"]
    result = None
    for pid in _LOCAL_PROBE_ORDER:
        ep = _endpoint(pid)
        if ep is None:
            continue
        _, base, key = ep
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{base}/models",
                                        headers={"Authorization": f"Bearer {key}"} if key else {})
                resp.raise_for_status()
                items = resp.json().get("data", [])
                models = sorted(m.get("id", "") for m in items if isinstance(m, dict) and m.get("id"))
                if models:
                    result = (pid, models[0])
                    log.info("auto-detected local LLM: %s -> %s", pid, models[0])
                    break
        except (httpx.HTTPError, ValueError, KeyError):
            continue
    _detect_cache.update(ts=time.time(), result=result)
    return result


async def _candidates(role: str) -> list[tuple[str, str]]:
    active_provider = env_value("LLM_PROVIDER")
    out: list[tuple[str, str]] = []

    if role:
        ref = env_value(f"LLM_MODEL_{role.upper()}")
        parsed = _parse_model_ref(ref, active_provider) if ref else None
        if parsed:
            out.append(parsed)

    if active_provider:
        from app.llm_providers import get_provider
        p = get_provider(active_provider)
        model = env_value("LLM_MODEL") or (p["default_model"] if p else "")
        if model:
            out.append((active_provider, model))

    for item in env_value("LLM_ROTATION").split(","):
        parsed = _parse_model_ref(item, active_provider)
        if parsed:
            out.append(parsed)

    if env_value("LLM_BASE_URL") and not any(p == "custom" for p, _ in out):
        out.append(("custom", env_value("LLM_MODEL") or "gpt-4o-mini"))
    if env_value("ANTHROPIC_API_KEY"):
        out.append(("anthropic", env_value("LLM_MODEL") or "claude-sonnet-5"))
    if env_value("OPENAI_API_KEY"):
        out.append(("openai", env_value("LLM_MODEL") or "gpt-4o-mini"))

    detected = await _autodetect()
    if detected:
        out.append(detected)

    seen: set[tuple[str, str]] = set()
    return [c for c in out if not (c in seen or seen.add(c))]


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (401, 403, 404, 408, 429) or exc.response.status_code >= 500
    return isinstance(exc, httpx.RequestError)


async def _call(provider_id: str, model: str, prompt: str, system: str, max_tokens: int) -> str:
    ep = _endpoint(provider_id)
    if ep is None:
        raise LLMNotConfigured(f"provider '{provider_id}' has no endpoint configured")
    kind, base, key = ep

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


async def complete(prompt: str, system: str = "", max_tokens: int = 4000, role: str = "") -> str:
    candidates = await _candidates(role)
    if not candidates:
        raise LLMNotConfigured(
            "No LLM available. Add a provider key on the Models page, or start a local runtime "
            "(FreeLLMAPI :3002, Ollama :11434, LM Studio :1234) — DevFoundry auto-detects them.")

    errors: list[str] = []
    for provider_id, model in candidates:
        try:
            result = await _call(provider_id, model, prompt, system, max_tokens)
            if errors:
                log.info("rotation: %s:%s succeeded after %d failure(s)", provider_id, model, len(errors))
            return result
        except Exception as exc:  # noqa: BLE001 — rotate on retryable, raise otherwise
            if _retryable(exc) or isinstance(exc, LLMNotConfigured):
                msg = f"{provider_id}:{model} -> {str(exc)[:160]}"
                log.warning("rotating: %s", msg)
                errors.append(msg)
                continue
            raise
    raise LLMNotConfigured("All LLM candidates failed:\n" + "\n".join(errors))


async def routing_info() -> dict:
    detected = await _autodetect()
    return {
        "active_provider": env_value("LLM_PROVIDER"),
        "active_model": env_value("LLM_MODEL"),
        "rotation": [s.strip() for s in env_value("LLM_ROTATION").split(",") if s.strip()],
        "stage_experts": {r: env_value(f"LLM_MODEL_{r.upper()}")
                          for r in ("spec", "codegen", "tasks", "refine")
                          if env_value(f"LLM_MODEL_{r.upper()}")},
        "autodetected_local": {"provider": detected[0], "model": detected[1]} if detected else None,
    }
