"""Embedded pipeline: every stage runs in-process — no Docker, no sidecars.

This is the default mode. The five stages mirror the service contracts exactly,
so the UI sees identical events either way. Docker ("isolated mode") remains
available for containerized deploys and heavyweight engines.
"""
import asyncio
import json
import logging
import os
import re
import shutil
from pathlib import Path

from app.events.bus import bus
from app.llm import complete
from app.models.schemas import PipelineEvent, RunState, Stage

log = logging.getLogger(__name__)

MAX_REFINE_ITERATIONS = 3
CODEGEN_SYSTEM = (
    "You are an expert full-stack engineer. Generate a complete, runnable application. "
    'Respond with ONLY a JSON object: {"files": {"relative/path": "file content", ...}}. '
    "Include a package manifest, entrypoint, README, and at least one test. Raw JSON only."
)


async def _emit(run_id: str, stage: Stage, message: str, kind: str = "log", **payload) -> None:
    await bus.publish(PipelineEvent(run_id=run_id, stage=stage, kind=kind, message=message, payload=payload))


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("model returned no JSON object")
    return json.loads(match.group(0))


def _snapshot(project_dir: Path, max_bytes: int = 60000) -> dict[str, str]:
    files: dict[str, str] = {}
    used = 0
    for p in sorted(project_dir.rglob("*")):
        if p.is_dir() or any(part.startswith(".") or part in ("node_modules", "__pycache__") for part in p.parts):
            continue
        if used >= max_bytes:
            break
        try:
            content = p.read_text()[:6000]
        except (UnicodeDecodeError, OSError):
            continue
        files[str(p.relative_to(project_dir))] = content
        used += len(content)
    return files


def _write_files(project_dir: Path, files: dict[str, str]) -> list[str]:
    written = []
    root = project_dir.resolve()
    for rel, content in files.items():
        target = (project_dir / rel).resolve()
        if not str(target).startswith(str(root)):
            log.warning("skipping path-traversal entry: %s", rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content))
        written.append(rel)
    return written


async def _run_cmd(args: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, out.decode(errors="replace")
    except FileNotFoundError:
        return -1, f"{args[0]}: not installed"
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "timed out"


# ---------------------------------------------------------------- stages

async def spec_stage(run_id: str, idea: str) -> dict:
    await _emit(run_id, Stage.SPEC, "Assembling virtual team (PM, Architect, API designer)...")
    prd, arch, api = await asyncio.gather(
        complete(f"Write a concise PRD (goals, users, core features, success metrics) for: {idea}",
                 "You are a senior Product Manager.", role="spec"),
        complete(f"Design the system architecture (components, data flow, stack, ASCII diagram) for: {idea}",
                 "You are a principal Software Architect.", role="spec"),
        complete(f"Define the REST API (resources, endpoints, schemas) in markdown for: {idea}",
                 "You are an API designer.", role="spec"),
    )
    specs = {"prd": prd, "architecture": arch, "api_spec": api}
    for name, doc in specs.items():
        await _emit(run_id, Stage.SPEC, f"Produced {name}", kind="artifact", artifact=name, content=doc)
    return specs


async def codegen_stage(run_id: str, idea: str, specs: dict, project_dir: Path) -> list[str]:
    await _emit(run_id, Stage.CODEGEN, "Generating full application codebase...")
    text = await complete(
        f"Build this application: {idea}\n\n## PRD\n{specs['prd'][:6000]}\n\n"
        f"## Architecture\n{specs['architecture'][:4000]}\n\n## API Spec\n{specs['api_spec'][:4000]}",
        CODEGEN_SYSTEM, max_tokens=16000, role="codegen")
    data = _extract_json(text)
    files = data.get("files", data)
    if not isinstance(files, dict) or not files:
        raise ValueError("codegen produced no files")
    written = _write_files(project_dir, files)
    await _emit(run_id, Stage.CODEGEN, f"Generated {len(written)} files", kind="artifact",
                artifact="codebase_manifest", files=sorted(written))
    return written


async def tasks_stage(run_id: str, specs: dict, files: list[str]) -> list[dict]:
    await _emit(run_id, Stage.TASKS, "Decomposing features into developer tasks...")
    text = await complete(
        "Break this PRD into 3-8 concrete development tasks. "
        'Return ONLY a JSON array of {"title": ..., "description": ...}.\n\n'
        f"PRD:\n{specs['prd'][:8000]}\n\nExisting files:\n" + "\n".join(files[:100]),
        "You are an engineering lead planning a sprint.", role="tasks")
    match = re.search(r"\[[\s\S]*\]", text)
    raw = json.loads(match.group(0)) if match else []
    devs = ["ai-dev-1", "ai-dev-2", "ai-dev-3"]
    tasks = [{"id": f"t{i+1}", "title": t.get("title", f"Task {i+1}"),
              "description": t.get("description", ""), "assignee": devs[i % 3], "status": "todo"}
             for i, t in enumerate(raw)]
    await _emit(run_id, Stage.TASKS, f"Created {len(tasks)} tasks", kind="artifact",
                artifact="task_board", tasks=tasks)
    return tasks


async def refine_task(run_id: str, project_dir: Path, title: str, instruction: str) -> None:
    await _emit(run_id, Stage.REFINE, f"Working on '{title}'...")
    text = await complete(
        f"Project files:\n{json.dumps(_snapshot(project_dir))}\n\nTask: {instruction}\n\n"
        'Respond with ONLY JSON: {"files": {"path": "new full content"}, "summary": "..."} '
        "containing every file you modified or created.",
        "You are an expert software engineer performing a focused code change.", max_tokens=12000, role="refine")
    result = _extract_json(text)
    changed = _write_files(project_dir, result.get("files", {}))
    await _emit(run_id, Stage.REFINE, f"Changed {len(changed)} files for '{title}'", kind="artifact",
                artifact="diff", task=title, changed_files=changed, summary=result.get("summary", ""))


async def test_stage(run_id: str, project_dir: Path) -> dict:
    await _emit(run_id, Stage.REFINE, "Running test suite...")
    for args in (["python3", "-m", "pytest", "-q"], ["npm", "test", "--silent"]):
        marker = "pytest.ini" if args[0] == "python3" else "package.json"
        if args[0] == "python3" and not list(project_dir.rglob("test_*.py")) and not list(project_dir.rglob("*_test.py")):
            continue
        if args[0] == "npm" and not (project_dir / marker).exists():
            continue
        code, out = await _run_cmd(args, project_dir)
        result = {"passed": 1 if code == 0 else 0, "failed": 0 if code == 0 else 1, "failures": out[-3000:] if code else ""}
        await _emit(run_id, Stage.REFINE, "Tests passed" if code == 0 else "Tests failed", kind="status", **result)
        return result
    await _emit(run_id, Stage.REFINE, "No runnable test suite detected — skipping", kind="status", passed=0, failed=0)
    return {"passed": 0, "failed": 0}


async def _deploy_docker(run_id: str, project_dir: Path) -> dict | None:
    if not shutil.which("docker"):
        return None
    code, _ = await _run_cmd(["docker", "info"], project_dir, timeout=15)
    if code != 0:
        return None
    tag = f"devfoundry-app:{run_id[:8]}"
    code, out = await _run_cmd(["docker", "build", "-t", tag, str(project_dir)], project_dir, timeout=600)
    if code != 0:
        await _emit(run_id, Stage.DEPLOY, "Container build failed — falling back", kind="log")
        return None
    return {"provider": "docker", "image": tag, "logs": out[-2000:]}


async def deploy_stage(run_id: str, project_dir: Path, workspace: Path, deploy_config: dict | None = None) -> dict:
    from app.config import env_value
    from app.orchestrator.deploy_providers import (
        DeployError, deploy_cloudflare_pages, deploy_hf_space, deploy_netlify,
        deploy_surge, deploy_vercel, write_zip)

    cfg = deploy_config or {}
    target = (cfg.get("target") or env_value("DEPLOY_TARGET") or "auto").strip().lower()
    domain = (cfg.get("domain") or "").strip()
    await _emit(run_id, Stage.DEPLOY, f"Deploying (target: {target}{', domain: ' + domain if domain else ''})...")
    try:
        result: dict | None = None
        if target == "netlify":
            result = await deploy_netlify(project_dir, domain)
        elif target in ("hf-spaces", "hf", "huggingface"):
            result = await deploy_hf_space(project_dir, run_id)
        elif target == "vercel":
            result = await deploy_vercel(project_dir)
        elif target == "cloudflare-pages":
            result = await deploy_cloudflare_pages(project_dir, run_id)
        elif target == "surge":
            result = await deploy_surge(project_dir, run_id, domain)
        elif target == "docker":
            result = await _deploy_docker(run_id, project_dir)
            if result is None:
                raise DeployError("Docker deploy requested but Docker is not available")
        elif target == "zip":
            result = write_zip(project_dir, workspace)
        else:  # auto
            result = await _deploy_docker(run_id, project_dir) or write_zip(project_dir, workspace)
        await _emit(run_id, Stage.DEPLOY,
                    f"Deployed via {result.get('provider')}: {result.get('url') or result.get('image') or result.get('bundle')}",
                    kind="artifact", artifact="deployment", **result)
        return result
    except DeployError as exc:
        await _emit(run_id, Stage.DEPLOY, f"{exc} — packaging zip bundle instead", kind="log")
        result = write_zip(project_dir, workspace)
        await _emit(run_id, Stage.DEPLOY, f"Packaged app bundle: {result['bundle']}",
                    kind="artifact", artifact="deployment", **result)
        return result


# ---------------------------------------------------------------- pipeline

async def run_embedded_pipeline(state: RunState, set_stage, workspace: Path) -> None:
    run_id = state.run_id
    project_dir = workspace / "app"
    project_dir.mkdir(parents=True, exist_ok=True)

    await set_stage(state, Stage.SPEC, "Generating specifications")
    specs = await spec_stage(run_id, state.idea)
    state.artifacts["specs"] = specs

    await set_stage(state, Stage.CODEGEN, "Generating codebase")
    files = await codegen_stage(run_id, state.idea, specs, project_dir)
    state.artifacts["project_dir"] = str(project_dir)

    await set_stage(state, Stage.TASKS, "Planning tasks")
    tasks = await tasks_stage(run_id, specs, files)
    state.artifacts["tasks"] = tasks

    await set_stage(state, Stage.REFINE, "Refining code")
    for task in tasks:
        await refine_task(run_id, project_dir, task["title"], task["description"] or task["title"])
    for i in range(MAX_REFINE_ITERATIONS):
        results = await test_stage(run_id, project_dir)
        if results.get("failed", 0) == 0:
            break
        await refine_task(run_id, project_dir, f"Fix failing tests (iteration {i+1})",
                          f"Fix these test failures:\n{results.get('failures', '')}")

    await set_stage(state, Stage.DEPLOY, "Packaging & deploying")
    state.artifacts["deployment"] = await deploy_stage(
        run_id, project_dir, workspace, state.artifacts.get("deploy_config"))

    await set_stage(state, Stage.DONE, "Pipeline complete")
