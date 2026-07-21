# Router research notes — toward an entropy-based dynamic router

Design input for evolving DevFoundry's LLM routing (today: MoE stage experts + a static
rotation/failover chain + free-provider auto-router). These techniques are **not yet
implemented** — they're the researched direction for v0.3+.

## Candidate techniques

### MoA (Mixture of Agents) — ensemble engine
Core ops: `Propose` (parallel initial responses) → `Synthesize` (each agent digests all
outputs) → `Aggregate` (one model merges) — plus `Refine`, `Rank(n)`, `Vote`.
Robustness transforms: `Shuffle()` (kills position bias), `Dropout(rate)`.
Known problem: all-to-all agent connectivity is redundant and under-utilizes hardware.

### Self-MoA — single-model ensemble
Same aggregation loop but sampling one strong model repeatedly instead of many weak ones;
often beats heterogeneous MoA when one model dominates the pool.

### ToT (Tree of Thoughts) — deliberative planner
Loop: **Expand** (generate candidate paths) → **Score** (evaluate) → **Prune** (keep best).
Search: BFS with beam width *b*, or DFS with backtracking. Reported gains: pruning cuts
processing ~30%; parallel exploration converges up to ~5×.

### Entropy-guided dynamic routing
A small router (~1.5B classifier) predicts input entropy and picks the reasoning depth:
- low entropy (confident) → shallow CoT / fewer experts / small local model
- high entropy (uncertain) → deep ToT / more experts / larger model
Adaptive-K expert selection reports 24–33% compute reduction on MoE models
(Mixtral 8×7B 31.0%, Qwen-MoE 32.4%, OLMoE 24.7%, Nemotron Nano 33.3%); composed with
4-bit quantization + speculative decoding, up to ~96% total compute reduction at <0.5%
perplexity cost. Token-by-token variants hand off between a local model and an API model
as confidence shifts (hybrid-llm); DynMoLE uses Tsallis entropy with top-p/top-k hybrid
routing plus an auxiliary entropy loss.

## How this maps onto DevFoundry

| Today | v0.3 direction |
|---|---|
| Static `LLM_ROTATION` failover | Entropy-scored routing: easy prompts → local model, hard → strongest provider |
| One codegen attempt + retry | Self-MoA on codegen: N samples from the strong model → Rank/Vote → best file map |
| Single-shot design brief | ToT on the design stage: expand 3 briefs → score vs. skills/KB → prune to 1 |
| Fixed stage experts | Adaptive depth per stage from a cheap entropy probe (first-token logprobs or a 1.5B judge) |

Practical first step: a `route_depth(prompt) -> shallow|deep|ensemble` heuristic using the
active local model's self-reported confidence, wired into `app/llm.py`'s candidate builder.
