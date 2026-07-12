"""Deployment providers for the embedded deploy stage.

Free targets:
- netlify:    free static hosting — zip deploy via the Netlify API (NETLIFY_AUTH_TOKEN)
- hf-spaces:  free CPU tier on Hugging Face Spaces (HF_TOKEN)
Local targets:
- docker:     build + tag a container image locally
- zip:        package the project as an archive (always works)
DEPLOY_TARGET=auto tries docker, falls back to zip.
"""
import io
import logging
import os
import zipfile
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


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


async def deploy_netlify(project_dir: Path) -> dict:
    """Create a new Netlify site and deploy the project as a static zip. Free tier."""
    token = os.environ.get("NETLIFY_AUTH_TOKEN", "")
    if not token:
        raise DeployError("NETLIFY_AUTH_TOKEN not set — add it in Settings (free account at netlify.com)")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=300) as client:
        site = await client.post("https://api.netlify.com/api/v1/sites", headers=headers, json={})
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
    return {"provider": "netlify", "url": url, "site_id": site_id, "free_tier": True}


async def deploy_hf_space(project_dir: Path, run_id: str) -> dict:
    """Create (or reuse) a Hugging Face Space and upload the project. Free CPU tier."""
    token = os.environ.get("HF_TOKEN", "")
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


def available_providers() -> list[dict]:
    return [
        {"id": "auto", "label": "Auto (Docker if available, else zip)", "free": True,
         "configured": True},
        {"id": "zip", "label": "Zip bundle (local)", "free": True, "configured": True},
        {"id": "docker", "label": "Docker image (local)", "free": True, "configured": True},
        {"id": "netlify", "label": "Netlify (free static hosting)", "free": True,
         "configured": bool(os.environ.get("NETLIFY_AUTH_TOKEN"))},
        {"id": "hf-spaces", "label": "Hugging Face Spaces (free CPU)", "free": True,
         "configured": bool(os.environ.get("HF_TOKEN"))},
    ]
