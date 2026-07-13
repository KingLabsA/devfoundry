"""Deployment providers for the embedded deploy stage.

Free targets:
- netlify:    free static hosting — zip deploy via the Netlify API (NETLIFY_AUTH_TOKEN)
- hf-spaces:  free CPU tier on Hugging Face Spaces (HF_TOKEN)
Local targets:
- docker:     build + tag a container image locally
- zip:        package the project as an archive (always works)
DEPLOY_TARGET=auto tries docker, falls back to zip.
"""
import asyncio
import io
import logging
import zipfile
from pathlib import Path

import httpx

from app.config import env_value

log = logging.getLogger(__name__)


async def _cli(args: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 600) -> tuple[int, str]:
    import os as _os
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=cwd, env={**_os.environ, **(env or {})},
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, out.decode(errors="replace")
    except FileNotFoundError:
        return -1, f"{args[0]}: not installed"
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "timed out"


class DeployError(RuntimeError):
    pass


def _zip_bytes(project_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in project_dir.rglob("*"):
            if p.is_file() and "node_modules" not in p.parts and ".git" not in p.parts:
                zf.write(p, p.relative_to(project_dir))
    return buf.getvalue()


def write_zip(project_dir: Path, workspace: Path) -> dict:
    archive = workspace / "app-bundle.zip"
    archive.write_bytes(_zip_bytes(project_dir))
    return {"provider": "zip", "bundle": str(archive)}


async def deploy_netlify(project_dir: Path, custom_domain: str = "") -> dict:
    """Create a new Netlify site and deploy the project as a static zip. Free tier.
    custom_domain: a full domain (foo.com) or bare subdomain used as the site name."""
    token = env_value("NETLIFY_AUTH_TOKEN")
    if not token:
        raise DeployError("NETLIFY_AUTH_TOKEN not set — add it in Settings (free account at netlify.com)")
    headers = {"Authorization": f"Bearer {token}"}
    site_body: dict = {}
    if custom_domain:
        if "." in custom_domain and not custom_domain.endswith(".netlify.app"):
            site_body["custom_domain"] = custom_domain
        else:
            site_body["name"] = custom_domain.replace(".netlify.app", "")
    async with httpx.AsyncClient(timeout=300) as client:
        site = await client.post("https://api.netlify.com/api/v1/sites", headers=headers, json=site_body)
        if site.status_code not in (200, 201):
            raise DeployError(f"Netlify site creation failed: {site.status_code} {site.text[:300]}")
        site_id = site.json()["id"]
        url = site.json().get("ssl_url") or site.json().get("url", "")
        deploy = await client.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            headers={**headers, "Content-Type": "application/zip"},
            content=_zip_bytes(project_dir),
        )
        if deploy.status_code not in (200, 201):
            raise DeployError(f"Netlify deploy failed: {deploy.status_code} {deploy.text[:300]}")
    return {"provider": "netlify", "url": url, "site_id": site_id,
            "custom_domain": custom_domain or None, "free_tier": True}


async def deploy_hf_space(project_dir: Path, run_id: str) -> dict:
    """Create (or reuse) a Hugging Face Space and upload the project. Free CPU tier."""
    token = env_value("HF_TOKEN")
    if not token:
        raise DeployError("HF_TOKEN not set — add it in Settings (free account at huggingface.co)")
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise DeployError("huggingface-hub not installed — run: pip install huggingface-hub")

    api = HfApi(token=token)
    user = api.whoami()["name"]
    repo_id = f"{user}/devfoundry-{run_id[:8]}"
    sdk = "gradio" if any(project_dir.rglob("app.py")) else "static"
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk=sdk, exist_ok=True)
    api.upload_folder(
        folder_path=str(project_dir), repo_id=repo_id, repo_type="space",
        ignore_patterns=["node_modules/*", ".git/*", "__pycache__/*"],
    )
    return {"provider": "hf-spaces", "url": f"https://huggingface.co/spaces/{repo_id}",
            "repo_id": repo_id, "sdk": sdk, "free_tier": True}


async def deploy_vercel(project_dir: Path) -> dict:
    """Deploy via the Vercel CLI (npx). Free hobby tier."""
    token = env_value("VERCEL_TOKEN")
    if not token:
        raise DeployError("VERCEL_TOKEN not set — add it in Settings (free account at vercel.com/account/tokens)")
    code, out = await _cli(["npx", "-y", "vercel", "deploy", "--prod", "--yes", "--token", token],
                           project_dir)
    if code != 0:
        raise DeployError(f"Vercel deploy failed: {out[-500:]}")
    url = next((w for w in out.split() if w.startswith("https://") and ".vercel.app" in w), "")
    return {"provider": "vercel", "url": url or out.strip().splitlines()[-1], "free_tier": True}


async def deploy_cloudflare_pages(project_dir: Path, run_id: str) -> dict:
    """Deploy static output to Cloudflare Pages via wrangler. Free tier."""
    token = env_value("CLOUDFLARE_API_TOKEN")
    account = env_value("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        raise DeployError("CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID not set — add them in Settings (free at dash.cloudflare.com)")
    project = f"devfoundry-{run_id[:8]}"
    env = {"CLOUDFLARE_API_TOKEN": token, "CLOUDFLARE_ACCOUNT_ID": account}
    await _cli(["npx", "-y", "wrangler", "pages", "project", "create", project,
                "--production-branch", "main"], project_dir, env)
    code, out = await _cli(["npx", "-y", "wrangler", "pages", "deploy", ".",
                            "--project-name", project, "--commit-dirty=true"], project_dir, env)
    if code != 0:
        raise DeployError(f"Cloudflare Pages deploy failed: {out[-500:]}")
    url = next((w for w in out.split() if w.startswith("https://") and ".pages.dev" in w),
               f"https://{project}.pages.dev")
    return {"provider": "cloudflare-pages", "url": url, "project": project, "free_tier": True}


async def deploy_surge(project_dir: Path, run_id: str, custom_domain: str = "") -> dict:
    """Deploy static files to surge.sh. Free. Supports a custom domain."""
    login = env_value("SURGE_LOGIN")
    token = env_value("SURGE_TOKEN")
    if not login or not token:
        raise DeployError("SURGE_LOGIN / SURGE_TOKEN not set — add them in Settings (free: npx surge token)")
    domain = custom_domain.strip() or f"devfoundry-{run_id[:8]}.surge.sh"
    code, out = await _cli(["npx", "-y", "surge", ".", domain], project_dir,
                           {"SURGE_LOGIN": login, "SURGE_TOKEN": token})
    if code != 0:
        raise DeployError(f"Surge deploy failed: {out[-500:]}")
    return {"provider": "surge", "url": f"https://{domain}",
            "custom_domain": custom_domain or None, "free_tier": True}


def available_providers() -> list[dict]:
    return [
        {"id": "auto", "label": "Auto (Docker if available, else zip)", "free": True,
         "configured": True},
        {"id": "zip", "label": "Zip bundle (local)", "free": True, "configured": True},
        {"id": "docker", "label": "Docker image (local)", "free": True, "configured": True},
        {"id": "netlify", "label": "Netlify (free static hosting)", "free": True,
         "configured": bool(env_value("NETLIFY_AUTH_TOKEN"))},
        {"id": "hf-spaces", "label": "Hugging Face Spaces (free CPU)", "free": True,
         "configured": bool(env_value("HF_TOKEN"))},
        {"id": "vercel", "label": "Vercel (free hobby tier)", "free": True,
         "configured": bool(env_value("VERCEL_TOKEN"))},
        {"id": "cloudflare-pages", "label": "Cloudflare Pages (free)", "free": True,
         "configured": bool(env_value("CLOUDFLARE_API_TOKEN") and env_value("CLOUDFLARE_ACCOUNT_ID"))},
        {"id": "surge", "label": "Surge.sh (free)", "free": True,
         "configured": bool(env_value("SURGE_LOGIN") and env_value("SURGE_TOKEN"))},
    ]
