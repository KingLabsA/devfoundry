"""Reasoning engine: user-selectable inference strategies for the pipeline.

Modes (chosen per run on the Forge page, or REASONING_MODE env default):
  fast      — single-shot everything (today's behavior; cheapest)
  balanced  — ToT on the design stage (expand K briefs → score → prune to 1)
  deep      — balanced + Self-MoA on codegen (N samples from the active model → judge ranks)
  ensemble  — balanced + MoA-lite on codegen (propose from DISTINCT providers → judge ranks)
  auto      — a cheap complexity probe routes to fast / balanced / deep / ensemble
              (entropy-INSPIRED: providers don't expose logprobs, so we probe with a
               1-10 complexity self-assessment instead of true token entropy)

Design notes: MoA here is Propose→Rank (winner-take-best), not full all-to-all
Synthesize — full synthesis of complete file maps is token-prohibitive and the
all-to-all topology is known-redundant. Judged ranking keeps the ensemble benefit
at ~N× cost instead of N²×.
"""
import asyncio
import json
import logging
import re

from app.config import env_value
from app.llm import complete

log = logging.getLogger(__name__)

MODES = ("fast", "balanced", "deep", "ensemble", "auto")


def reasoning_n() -> int:
    try:
        return max(2, min(4, int(env_value("REASONING_N") or "3")))
    except ValueError:
        return 3


async def assess_complexity(idea: str) -> int:
    """Cheap probe (fast/local-friendly): 1-10 task complexity."""
    try:
        text = await complete(
            f"Rate the engineering complexity of building this app on a 1-10 scale "
            f"(1=static page, 10=multi-service platform). Reply with ONLY the integer.\n\n{idea}",
            "You estimate software project complexity.", max_tokens=8, role="tasks")
        match = re.search(r"\d+", text)
        return min(10, max(1, int(match.group()))) if match else 5
    except Exception:  # noqa: BLE001 — probe failure must not block the run
        return 5


async def resolve_mode(mode: str, idea: str, emit) -> str:
    mode = (mode or env_value("REASONING_MODE") or "fast").strip().lower()
    if mode not in MODES:
        mode = "fast"
    if mode == "auto":
        score = await assess_complexity(idea)
        mode = "fast" if score <= 3 else "balanced" if score <= 6 else "deep" if score <= 8 else "ensemble"
        await emit(f"Auto-router: complexity {score}/10 → {mode} mode")
    return mode


async def _judge_pick(candidates: list[dict], criteria: str, describe) -> int:
    """Ask a judge to rank candidates; returns the winning index (0 on any failure)."""
    if len(candidates) == 1:
        return 0
    listing = "\n\n".join(f"### Candidate {i + 1}\n{describe(c)}" for i, c in enumerate(candidates))
    try:
        text = await complete(
            f"{criteria}\n\n{listing}\n\n"
            'Reply with ONLY JSON: {"best": <1-based index>, "reason": "<one line>"}',
            "You are a strict engineering judge. Pick the single best candidate.",
            max_tokens=200, role="refine")
        data = json.loads(re.search(r"\{[\s\S]*\}", text).group(0))
        best = int(data.get("best", 1)) - 1
        return best if 0 <= best < len(candidates) else 0
    except Exception:  # noqa: BLE001
        log.exception("judge failed — defaulting to first candidate")
        return 0


async def tot_design(idea: str, guidance: str, emit, k: int | None = None) -> str:
    """Tree-of-Thoughts (depth-1 beam): expand K briefs in parallel → judge prunes to 1."""
    k = k or reasoning_n()
    await emit(f"ToT design: expanding {k} candidate briefs...")
    angles = ["bold and editorial", "minimal and conversion-focused", "warm and product-led",
              "enterprise and trust-building"][:k]

    errors: list[str] = []

    async def one(angle: str) -> str | None:
        try:
            return await complete(
                f"Product idea: {idea}\n\n{guidance}\n\n"
                f"Write a concrete DESIGN BRIEF with a **{angle}** direction: brand color + palette, "
                "type hierarchy, page/section structure, key components, copy tone. Be specific.",
                "You are a world-class product designer.", max_tokens=1800, role="spec")
        except Exception as exc:  # noqa: BLE001 — collect, don't hide
            errors.append(f"{angle}: {str(exc)[:100]}")
            return None

    briefs = [b for b in await asyncio.gather(*(one(a) for a in angles)) if b]
    if errors:
        await emit(f"ToT design: {len(errors)} candidate(s) errored ({errors[0]})")
    if not briefs:
        raise RuntimeError(f"ToT design produced no briefs: {'; '.join(errors[:2])}")
    win = await _judge_pick(
        briefs,
        f"Which design brief will produce the best product for: {idea}? "
        "Score fit-to-idea, specificity, and buildability.",
        lambda b: b[:1200])
    await emit(f"ToT design: pruned {len(briefs)} → 1 (candidate {win + 1} selected)")
    return briefs[win]


def _distinct_provider_overrides(n: int) -> list[tuple[str, str] | None]:
    """For ensemble mode: up to n (provider, model) overrides from distinct configured
    providers; None entries fall back to the normal routing chain."""
    from app.llm_providers import catalog

    overrides: list[tuple[str, str] | None] = [None]  # first candidate: active chain
    for p in catalog():
        if len(overrides) >= n:
            break
        if p["configured"] and not p["active"] and p["default_model"]:
            overrides.append((p["id"], p["default_model"]))
    while len(overrides) < n:
        overrides.append(None)
    return overrides[:n]


async def candidate_codegen(prompt: str, system: str, parse, emit,
                            mode: str) -> dict[str, str]:
    """Self-MoA (deep) or MoA-lite (ensemble) codegen: N proposals → judge ranks → best.

    `parse` converts raw model text into a {path: content} map (raises on failure).
    Unparseable candidates are dropped; if all fail, raises the last error.
    """
    n = reasoning_n()
    overrides = _distinct_provider_overrides(n) if mode == "ensemble" else [None] * n
    label = "MoA ensemble (distinct providers)" if mode == "ensemble" else "Self-MoA (best-of-N)"
    await emit(f"{label}: generating {n} codebase candidates in parallel...")

    async def one(idx: int, override) -> dict[str, str] | None:
        try:
            text = await complete(prompt, system, max_tokens=16000, role="codegen", override=override)
            files = parse(text)
            return files or None
        except Exception as exc:  # noqa: BLE001
            log.info("codegen candidate %d failed: %s", idx + 1, str(exc)[:120])
            return None

    results = await asyncio.gather(*(one(i, o) for i, o in enumerate(overrides)))
    candidates = [r for r in results if r]
    await emit(f"{label}: {len(candidates)}/{n} candidates parseable")
    if not candidates:
        raise ValueError("all codegen candidates failed to parse")

    def describe(files: dict[str, str]) -> str:
        names = sorted(files.keys())
        entry = next((files[k] for k in names if k.endswith((".html", "App.tsx", "index.tsx"))), "")
        return f"{len(names)} files: {', '.join(names[:14])}\nEntry excerpt:\n{entry[:900]}"

    win = await _judge_pick(
        candidates,
        "Which candidate codebase is most complete, best structured, and most faithful to a "
        "premium design system (real copy, componentized, responsive, tested)?",
        describe)
    await emit(f"{label}: judge selected candidate {win + 1} of {len(candidates)}")
    return candidates[win]
