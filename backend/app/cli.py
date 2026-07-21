"""DevFoundry CLI — the factory from your terminal.

    devfoundry serve                        start the orchestrator (+ web app at /app)
    devfoundry forge "idea" [options]       run the full pipeline, stream progress
    devfoundry research "question"          deep research → cited markdown report
    devfoundry runs                         list build history
    devfoundry version                      version & credits

Created by King3Djbl of KingLabs — https://github.com/KingLabsA
"""
import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = "http://localhost:9100"
VERSION = "0.2.3"
CREDIT = ("DevFoundry v" + VERSION + " — the local-first AI software factory\n"
          "Created by King3Djbl of KingLabs · built with Claude Code · MIT license\n"
          "GitHub  https://github.com/KingLabsA/devfoundry\n"
          "HF      https://huggingface.co/King3Djbl\n"
          "Ollama  https://ollama.com/FableForge-AI")


def _backend_up() -> bool:
    try:
        return httpx.get(f"{BASE}/api/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def _ensure_backend(auto: bool = True) -> bool:
    if _backend_up():
        return True
    if not auto:
        return False
    backend_dir = Path(__file__).resolve().parent.parent
    uvicorn = backend_dir / ".venv/bin/uvicorn"
    cmd = ([str(uvicorn)] if uvicorn.exists() else [sys.executable, "-m", "uvicorn"])
    cmd += ["app.main:app", "--host", "127.0.0.1", "--port", "9100"]
    print("• starting orchestrator...", file=sys.stderr)
    subprocess.Popen(cmd, cwd=backend_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if _backend_up():
            return True
        time.sleep(1)
    return False


def cmd_serve(args) -> int:
    if _backend_up():
        print(f"orchestrator already running — web app: {BASE}/app")
        return 0
    backend_dir = Path(__file__).resolve().parent.parent
    uvicorn = backend_dir / ".venv/bin/uvicorn"
    cmd = ([str(uvicorn)] if uvicorn.exists() else [sys.executable, "-m", "uvicorn"])
    cmd += ["app.main:app", "--host", args.host, "--port", str(args.port)]
    print(f"DevFoundry orchestrator on http://{args.host}:{args.port} — web app at /app (Ctrl-C to stop)")
    return subprocess.call(cmd, cwd=backend_dir)


async def _stream_run(run_id: str) -> str:
    stage = "queued"
    try:
        import websockets  # optional dependency; fall back to polling without it
        async with websockets.connect(f"ws://localhost:9100/ws/runs/{run_id}") as ws:
            while True:
                msg = json.loads(await ws.recv())
                stage = msg.get("stage", stage)
                print(f"  [{stage}] {msg.get('message', '')}")
                if msg.get("kind") == "status" and stage in ("done", "failed"):
                    return stage
    except ImportError:
        seen = 0
        while True:
            await asyncio.sleep(3)
            events = httpx.get(f"{BASE}/api/runs/{run_id}/events", timeout=10).json()
            for e in events[seen:]:
                stage = e.get("stage", stage)
                print(f"  [{stage}] {e.get('message', '')}")
            seen = len(events)
            if stage in ("done", "failed"):
                return stage


def cmd_forge(args) -> int:
    if not _ensure_backend():
        print("✗ orchestrator did not start — run `devfoundry serve` in another terminal", file=sys.stderr)
        return 1
    body = {"idea": args.idea, "skills": args.skill or [],
            "reasoning": args.reasoning, "deploy_target": args.deploy}
    resp = httpx.post(f"{BASE}/api/runs", json=body, timeout=15)
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"⬢ forging {run_id[:8]} — {args.idea}")
    stage = asyncio.run(_stream_run(run_id))
    if stage == "done":
        run = httpx.get(f"{BASE}/api/runs/{run_id}", timeout=10).json()
        dep = run.get("artifacts", {}).get("deployment", {})
        out = dep.get("url") or dep.get("image") or dep.get("bundle") or run["artifacts"].get("project_dir", "")
        print(f"✓ done — {out}")
        return 0
    print("✗ failed — see `devfoundry runs`")
    return 1


def cmd_research(args) -> int:
    if not _ensure_backend():
        print("✗ orchestrator did not start", file=sys.stderr)
        return 1

    async def go() -> int:
        try:
            import websockets
        except ImportError:
            print("research streaming needs: pip install websockets", file=sys.stderr)
            return 1
        async with websockets.connect(f"ws://localhost:9100/api/research/ws") as ws:
            await ws.send(json.dumps({"question": args.question, "depth": args.depth}))
            while True:
                msg = json.loads(await ws.recv())
                if msg["type"] == "step":
                    print(f"  • {msg['message']}", file=sys.stderr)
                elif msg["type"] == "result":
                    print(msg["report"])
                    if args.out:
                        Path(args.out).write_text(msg["report"])
                        print(f"\n(saved to {args.out})", file=sys.stderr)
                    return 0
                elif msg["type"] == "error":
                    print(f"✗ {msg['message']}", file=sys.stderr)
                    return 1
    return asyncio.run(go())


def cmd_runs(_args) -> int:
    if not _backend_up():
        print("orchestrator not running — `devfoundry serve`", file=sys.stderr)
        return 1
    for r in httpx.get(f"{BASE}/api/runs", timeout=10).json()[:20]:
        print(f"  {r['run_id'][:8]}  {r['stage']:<8}  {r['idea'][:70]}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="devfoundry", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("serve", help="start the orchestrator + web app")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=9100)
    s.set_defaults(fn=cmd_serve)

    f = sub.add_parser("forge", help="run the pipeline on an idea")
    f.add_argument("idea")
    f.add_argument("--skill", action="append", help="e.g. premium-landing (repeatable)")
    f.add_argument("--reasoning", default="fast", choices=["fast", "balanced", "deep", "ensemble", "auto"])
    f.add_argument("--deploy", default="zip")
    f.set_defaults(fn=cmd_forge)

    r = sub.add_parser("research", help="deep research → cited report")
    r.add_argument("question")
    r.add_argument("--depth", type=int, default=4)
    r.add_argument("--out", help="save report to a .md file")
    r.set_defaults(fn=cmd_research)

    sub.add_parser("runs", help="list build history").set_defaults(fn=cmd_runs)
    sub.add_parser("version", help="version & credits").set_defaults(fn=lambda a: print(CREDIT) or 0)

    args = p.parse_args()
    if not getattr(args, "fn", None):
        p.print_help()
        sys.exit(0)
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
