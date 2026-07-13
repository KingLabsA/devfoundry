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

# Delimited file format — robust across all models because file contents (quotes,
# braces, backslashes) never need escaping, unlike a JSON blob.
CODEGEN_SYSTEM = (
    "You are a senior full-stack engineer and product designer at a top agency. Build a "
    "COMPLETE, polished, production-ready application that a client would happily pay for. "
    "Follow the provided design system and design brief exactly. Real content, no placeholders, "
    "no 'lorem ipsum', no 'Feature 1'. Responsive, accessible, and visually refined.\n"
    "Output EACH file using this exact format, and nothing else:\n"
    "=== FILE: relative/path/name.ext ===\n"
    "<full file content>\n"
    "=== FILE: next/file.ext ===\n"
    "<full file content>\n"
    "Include a package manifest with working scripts, an entrypoint, all components, styling, "
    "a README with run steps, and at least one test. "
    "Do NOT wrap files in JSON or markdown code fences. No commentary before or after."
)

_FILE_HEADER = re.compile(r"^===\s*FILE:\s*(.+?)\s*===\s*$", re.MULTILINE)


async def _emit(run_id: str, stage: Stage, message: str, kind: str = "log", **payload) -> None:
    await bus.publish(PipelineEvent(run_id=run_id, stage=stage, kind=kind, message=message, payload=payload))


def _strip_fences(text: str) -> str:
    return re.sub(r"^```[a-zA-Z0-9]*\s*|\s*```$", "", text.strip())


def _parse_files(text: str) -> dict[str, str]:
    """Parse the delimited '=== FILE: path ===' format into {path: content}."""
    matches = list(_FILE_HEADER.finditer(text))
    files: dict[str, str] = {}
    for i, m in enumerate(matches):
        path = m.group(1).strip().strip("`").strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.end():end].strip("\n")
        content = re.sub(r"^```[a-zA-Z0-9]*\n|\n```$", "", content)  # tolerate stray fences
        if path and ".." not in path:
            files[path] = content
    return files


def _extract_json(text: str) -> dict:
    """Fallback JSON parser with light repair (fences, trailing commas, smart quotes)."""
    cleaned = _strip_fences(text)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("model returned no JSON object")
    blob = match.group(0)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", blob)          # trailing commas
        repaired = repaired.replace("“", '"').replace("”", '"')  # smart quotes
        return json.loads(repaired)


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


async def _run_cmd(args: list[str], cwd: Path, timeout: int = 300,
                   env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = None
    try:
        full_env = {**os.environ, **(env or {})}
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=cwd, env=full_env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, out.decode(errors="replace")
    except FileNotFoundError:
        return -1, f"{args[0]}: not installed"
    except asyncio.TimeoutError:
        if proc:
            proc.kill()
        return -124, "timed out (test runner may be in watch mode)"


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


def _files_from_response(text: str) -> dict[str, str]:
    """Delimited format first; fall back to a JSON {files:{...}} blob."""
    files = _parse_files(text)
    if files:
        return files
    data = _extract_json(text)
    files = data.get("files", data)
    if not isinstance(files, dict) or not files:
        raise ValueError("no files in model response")
    return {str(k): str(v) for k, v in files.items()}


async def design_stage(run_id: str, idea: str, skills: list[str]) -> str:
    """Produce a concrete design brief the codegen stage must follow (premium quality)."""
    from app.skills import build_guidance

    await _emit(run_id, Stage.SPEC, "Lead Designer: preparing the design brief...")
    guidance = build_guidance(skills)
    brief = await complete(
        f"Product idea: {idea}\n\n{guidance}\n\n"
        "Write a concrete DESIGN BRIEF for this product: pick a brand color + palette, a type "
        "hierarchy, the page/section structure, key components, and the tone of the copy. "
        "Be specific and opinionated — this is the blueprint the engineers will build to.",
        "You are a world-class product designer producing agency-grade work.",
        max_tokens=2000, role="spec")
    await _emit(run_id, Stage.SPEC, "Produced design brief", kind="artifact", artifact="design_brief", content=brief)
    return brief


async def codegen_stage(run_id: str, idea: str, specs: dict, project_dir: Path,
                        skills: list[str] | None = None) -> list[str]:
    from app.knowledge import context_for
    from app.skills import build_guidance

    await _emit(run_id, Stage.CODEGEN, "Generating full application codebase...")
    skills = skills or []
    guidance = build_guidance(skills)
    knowledge = await context_for(idea)
    design_brief = specs.get("design_brief", "")
    prompt = (f"Build this application to a premium, production-ready standard: {idea}\n\n"
              f"## Design brief\n{design_brief[:3000]}\n\n"
              f"## PRD\n{specs['prd'][:4000]}\n\n"
              f"## Architecture\n{specs['architecture'][:2500]}\n\n"
              f"## API Spec\n{specs['api_spec'][:2500]}\n\n"
              f"{guidance}\n\n{knowledge}")
    files: dict[str, str] = {}
    last_err = ""
    for attempt in range(2):
        text = await complete(prompt, CODEGEN_SYSTEM, max_tokens=16000, role="codegen")
        try:
            files = _files_from_response(text)
            if files:
                break
        except (ValueError, json.JSONDecodeError) as exc:
            last_err = str(exc)
            await _emit(run_id, Stage.CODEGEN,
                        f"Retry {attempt + 1}: could not parse model output ({last_err[:80]})", kind="log")
            prompt += ("\n\nIMPORTANT: use ONLY the '=== FILE: path ===' format, "
                       "one header per file, raw file contents, no JSON, no code fences.")
    if not files:
        raise ValueError(f"codegen produced no parseable files: {last_err}")
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
        "Return every file you modified or created using the '=== FILE: path ===' format "
        "(one header per file, raw contents, no JSON, no code fences).",
        "You are an expert software engineer performing a focused code change.", max_tokens=12000, role="refine")
    summary = ""
    try:
        files = _files_from_response(text)
    except (ValueError, json.JSONDecodeError):
        files = {}
    # never write bookkeeping keys as project files
    files = {p: c for p, c in files.items() if p.lower() not in ("summary", "notes", "explanation")}
    changed = _write_files(project_dir, files)
    await _emit(run_id, Stage.REFINE, f"Changed {len(changed)} files for '{title}'", kind="artifact",
                artifact="diff", task=title, changed_files=changed, summary=summary)


# Output markers that mean "the test environment can't run", not "a test failed".
# We must not loop the refine-on-failure step for these — the model can't fix missing deps.
_SETUP_ERROR_MARKERS = (
    "cannot find module", "module not found", "modulenotfounderror",
    "no test specified", "command not found", "is not recognized",
    "cannot find package", "err_module_not_found", "no such file or directory",
    "missing script", "econnrefused", "importerror",
    # test-runner setup problems (not logic failures)
    "jsdom", "document is not defined", "window is not defined", "environment",
    "failed to load config", "no test files found", "watch mode", "timed out",
)

# Env that forces one-shot (non-watch) runs across common JS test runners.
_CI_ENV = {"CI": "true", "VITEST_MODE": "run"}

MAX_BUILD_FIX_ITERATIONS = 3


def _pkg(project_dir: Path) -> dict:
    pkg = project_dir / "package.json"
    if not pkg.exists():
        return {}
    try:
        return json.loads(pkg.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


async def _apply_fix(run_id: str, project_dir: Path, problem: str, errors: str) -> list[str]:
    """Ask the model to fix a concrete build/test error and write the changed files."""
    text = await complete(
        f"Project files:\n{json.dumps(_snapshot(project_dir, 90000))}\n\n"
        f"{problem}:\n{errors[:6000]}\n\n"
        "Return ONLY the files you changed to fix this, using the '=== FILE: path ===' format "
        "(raw contents, no JSON, no code fences). Fix the actual cause; keep the app working.",
        "You are a senior engineer fixing a real build/test error. Be precise and minimal.",
        max_tokens=12000, role="refine")
    try:
        files = _files_from_response(text)
    except (ValueError, json.JSONDecodeError):
        return []
    files = {p: c for p, c in files.items() if p.lower() not in ("summary", "notes", "explanation")}
    return _write_files(project_dir, files)


async def build_verify_stage(run_id: str, project_dir: Path) -> dict:
    """Really install, build, and test the generated app — iterating on real errors.

    Returns a verification record: {installed, builds, tests_pass, runnable, iterations}.
    """
    pkg = _pkg(project_dir)
    scripts = pkg.get("scripts", {})
    is_node = bool(pkg)
    is_python = bool(list(project_dir.rglob("requirements.txt")) or list(project_dir.rglob("pyproject.toml")))
    verdict = {"installed": None, "builds": None, "tests_pass": None, "runnable": True, "iterations": 0}

    if not is_node and not is_python:
        await _emit(run_id, Stage.REFINE, "No build system detected — skipping verification",
                    kind="status", **verdict, runnable=False)
        verdict["runnable"] = False
        return verdict

    # 1. install
    if is_node and not (project_dir / "node_modules").exists():
        await _emit(run_id, Stage.REFINE, "Installing dependencies (npm install)...")
        code, out = await _run_cmd(["npm", "install", "--no-audit", "--no-fund"], project_dir, timeout=300, env=_CI_ENV)
        verdict["installed"] = code == 0
        if code != 0:
            await _emit(run_id, Stage.REFINE, "Dependency install failed — verification limited",
                        kind="status", **verdict)
            return verdict
    elif is_python:
        req = project_dir / "requirements.txt"
        if req.exists():
            await _emit(run_id, Stage.REFINE, "Installing Python dependencies...")
            code, _ = await _run_cmd(["python3", "-m", "pip", "install", "-q", "-r", str(req)], project_dir, timeout=300)
            verdict["installed"] = code == 0

    # 2. build (compile / typecheck) — iterate on real errors
    build_cmd = None
    if is_node and "build" in scripts:
        build_cmd = ["npm", "run", "build"]
    if build_cmd:
        for i in range(MAX_BUILD_FIX_ITERATIONS):
            await _emit(run_id, Stage.REFINE, f"Building the app ({' '.join(build_cmd)})...")
            code, out = await _run_cmd(build_cmd, project_dir, timeout=240, env=_CI_ENV)
            verdict["builds"] = code == 0
            verdict["iterations"] = i
            if code == 0:
                await _emit(run_id, Stage.REFINE, "✓ Build succeeded", kind="status", **verdict)
                break
            await _emit(run_id, Stage.REFINE, f"Build failed — fixing (iteration {i + 1})", kind="log")
            changed = await _apply_fix(run_id, project_dir, "The build failed with these errors", out)
            if not changed:
                await _emit(run_id, Stage.REFINE, "Could not auto-fix the build error", kind="log")
                break
        else:
            await _emit(run_id, Stage.REFINE, "Build still failing after fixes", kind="status", **verdict)

    # 3. tests — one-shot, iterate on genuine failures
    test_result = await test_stage(run_id, project_dir)
    if not test_result.get("runnable"):
        verdict["tests_pass"] = None
    else:
        verdict["tests_pass"] = test_result.get("failed", 1) == 0
        for i in range(MAX_BUILD_FIX_ITERATIONS):
            if verdict["tests_pass"]:
                break
            changed = await _apply_fix(run_id, project_dir, "These tests failed", test_result.get("failures", ""))
            if not changed:
                break
            test_result = await test_stage(run_id, project_dir)
            if not test_result.get("runnable"):
                break
            verdict["tests_pass"] = test_result.get("failed", 1) == 0

    status = ("verified" if verdict["builds"] and verdict.get("tests_pass") in (True, None)
              else "built" if verdict["builds"]
              else "unverified")
    await _emit(run_id, Stage.REFINE,
                f"Verification: {status} (installed={verdict['installed']}, builds={verdict['builds']}, "
                f"tests={verdict['tests_pass']})",
                kind="artifact", artifact="verification", status=status, **verdict)
    return {**verdict, "status": status}


def _has_real_npm_test(project_dir: Path) -> bool:
    pkg = project_dir / "package.json"
    if not pkg.exists():
        return False
    try:
        test = json.loads(pkg.read_text()).get("scripts", {}).get("test", "")
    except (json.JSONDecodeError, OSError):
        return False
    return bool(test) and "no test specified" not in test.lower()


async def test_stage(run_id: str, project_dir: Path) -> dict:
    await _emit(run_id, Stage.REFINE, "Running test suite...")
    has_py = bool(list(project_dir.rglob("test_*.py")) or list(project_dir.rglob("*_test.py")))
    has_js = _has_real_npm_test(project_dir)

    if has_py:
        runner = ["python3", "-m", "pytest", "-q"]
    elif has_js:
        if not (project_dir / "node_modules").exists():
            await _emit(run_id, Stage.REFINE, "Installing dependencies (npm install)...")
            icode, iout = await _run_cmd(["npm", "install", "--no-audit", "--no-fund"],
                                         project_dir, timeout=300, env=_CI_ENV)
            if icode != 0:
                await _emit(run_id, Stage.REFINE, "Dependency install failed — skipping tests",
                            kind="status", passed=0, failed=0, runnable=False)
                return {"passed": 0, "failed": 0, "runnable": False}
        # `npm test -- --run` forces vitest one-shot; harmless for other runners.
        runner = ["npm", "test", "--silent", "--", "--run"]
    else:
        await _emit(run_id, Stage.REFINE, "No runnable test suite — skipping", kind="status",
                    passed=0, failed=0, runnable=False)
        return {"passed": 0, "failed": 0, "runnable": False}

    # CI=true makes vitest/jest/etc. run once and exit (no watch-mode hang). 150s cap.
    code, out = await _run_cmd(runner, project_dir, timeout=150, env=_CI_ENV)
    low = out.lower()
    if code == -124 or (code != 0 and any(m in low for m in _SETUP_ERROR_MARKERS)):
        reason = "watch-mode/timeout" if code == -124 else "environment not runnable"
        await _emit(run_id, Stage.REFINE, f"Tests skipped ({reason}) — not a code failure",
                    kind="status", passed=0, failed=0, runnable=False)
        return {"passed": 0, "failed": 0, "runnable": False}
    result = {"passed": 1 if code == 0 else 0, "failed": 0 if code == 0 else 1,
              "failures": out[-3000:] if code else "", "runnable": True}
    await _emit(run_id, Stage.REFINE, "Tests passed" if code == 0 else "Tests failed", kind="status", **result)
    return result


async def _deploy_docker(run_id: str, project_dir: Path, require_dockerfile: bool = False) -> dict | None:
    if require_dockerfile and not (project_dir / "Dockerfile").exists():
        return None  # in auto mode, don't attempt a build the project isn't set up for
    if not shutil.which("docker"):
        return None
    code, _ = await _run_cmd(["docker", "info"], project_dir, timeout=15)
    if code != 0:
        return None
    tag = f"devfoundry-app:{run_id[:8]}"
    code, out = await _run_cmd(["docker", "build", "-t", tag, str(project_dir)], project_dir, timeout=600)
    if code != 0:
        await _emit(run_id, Stage.DEPLOY, "Container build failed — packaging zip instead", kind="log")
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
        else:  # auto — Docker only if the project ships a Dockerfile, else zip bundle
            result = await _deploy_docker(run_id, project_dir, require_dockerfile=True) or write_zip(project_dir, workspace)
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

    skills = state.artifacts.get("skills", [])

    await set_stage(state, Stage.SPEC, "Generating specifications & design")
    specs = await spec_stage(run_id, state.idea)
    specs["design_brief"] = await design_stage(run_id, state.idea, skills)
    state.artifacts["specs"] = specs

    await set_stage(state, Stage.CODEGEN, "Generating codebase")
    files = await codegen_stage(run_id, state.idea, specs, project_dir, skills)
    state.artifacts["project_dir"] = str(project_dir)

    await set_stage(state, Stage.TASKS, "Planning tasks")
    tasks = await tasks_stage(run_id, specs, files)
    state.artifacts["tasks"] = tasks

    await set_stage(state, Stage.REFINE, "Refining code")
    for task in tasks:
        await refine_task(run_id, project_dir, task["title"], task["description"] or task["title"])

    # Real build-verify: install → build (fix real errors) → test (fix real failures).
    state.artifacts["verification"] = await build_verify_stage(run_id, project_dir)

    await set_stage(state, Stage.DEPLOY, "Packaging & deploying")
    state.artifacts["deployment"] = await deploy_stage(
        run_id, project_dir, workspace, state.artifacts.get("deploy_config"))

    await set_stage(state, Stage.DONE, "Pipeline complete")
