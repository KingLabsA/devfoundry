"""Project file browser: list, read, edit, download (zip), upload (zip) a run's
generated codebase. All paths are confined to the run's workspace directory."""
import io
import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/runs")

_IGNORED = {"node_modules", "__pycache__", ".git", ".venv"}
_MAX_EDIT_BYTES = 2 * 1024 * 1024


class FileWrite(BaseModel):
    path: str
    content: str


def _run_root(run_id: str) -> Path:
    # run ids are hex; reject anything else before touching the filesystem
    if not run_id.isalnum():
        raise HTTPException(400, "invalid run id")
    root = (get_settings().devfoundry_workspace / run_id).resolve()
    if not root.is_dir():
        raise HTTPException(404, "run workspace not found")
    return root


def _safe_target(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    if root not in target.parents and target != root:
        raise HTTPException(400, "path escapes run workspace")
    return target


@router.get("/{run_id}/files")
async def list_files(run_id: str) -> list[dict]:
    root = _run_root(run_id)
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_dir() or any(part in _IGNORED for part in p.relative_to(root).parts):
            continue
        out.append({"path": str(p.relative_to(root)), "size": p.stat().st_size})
    return out


@router.get("/{run_id}/file")
async def read_file(run_id: str, path: str) -> dict:
    target = _safe_target(_run_root(run_id), path)
    if not target.is_file():
        raise HTTPException(404, "file not found")
    if target.stat().st_size > _MAX_EDIT_BYTES:
        raise HTTPException(413, "file too large to edit in-app")
    try:
        return {"path": path, "content": target.read_text(), "binary": False}
    except UnicodeDecodeError:
        return {"path": path, "content": "", "binary": True}


@router.put("/{run_id}/file")
async def write_file(run_id: str, body: FileWrite) -> dict:
    root = _run_root(run_id)
    target = _safe_target(root, body.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.content)
    return {"path": body.path, "size": target.stat().st_size, "saved": True}


@router.delete("/{run_id}/file")
async def delete_file(run_id: str, path: str) -> dict:
    target = _safe_target(_run_root(run_id), path)
    if not target.is_file():
        raise HTTPException(404, "file not found")
    target.unlink()
    return {"path": path, "deleted": True}


@router.get("/{run_id}/download")
async def download_zip(run_id: str) -> StreamingResponse:
    root = _run_root(run_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            if p.is_file() and not any(part in _IGNORED for part in p.relative_to(root).parts):
                zf.write(p, p.relative_to(root))
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="devfoundry-{run_id[:8]}.zip"'})


@router.post("/{run_id}/upload")
async def upload_zip(run_id: str, file: UploadFile) -> dict:
    root = _run_root(run_id)
    data = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(400, "not a valid zip file")
    written = 0
    for name in zf.namelist():
        if name.endswith("/") or any(part in _IGNORED for part in Path(name).parts) or ".." in Path(name).parts:
            continue
        target = _safe_target(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(name))
        written += 1
    return {"uploaded": written, "run_id": run_id}
