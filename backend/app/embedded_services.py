"""Embedded native services — no Docker required.

Qdrant ships official single-binary releases; DevFoundry downloads the right one
for this OS/arch once (into <workspace>/bin), then runs and supervises it as a
child process. This replaces the Docker container for vector-store RAG.
"""
import asyncio
import logging
import platform
import subprocess
import tarfile
import zipfile
from pathlib import Path

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

_proc: subprocess.Popen | None = None
QDRANT_PORT = 6333


def _bin_dir() -> Path:
    d = (get_settings().devfoundry_workspace / "bin").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _qdrant_bin() -> Path:
    name = "qdrant.exe" if platform.system() == "Windows" else "qdrant"
    return _bin_dir() / name


def _asset_name() -> str:
    sysname = platform.system()
    arch = platform.machine().lower()
    if sysname == "Darwin":
        return "qdrant-aarch64-apple-darwin.tar.gz" if arch in ("arm64", "aarch64") \
            else "qdrant-x86_64-apple-darwin.tar.gz"
    if sysname == "Windows":
        return "qdrant-x86_64-pc-windows-msvc.zip"
    return "qdrant-aarch64-unknown-linux-gnu.tar.gz" if arch in ("arm64", "aarch64") \
        else "qdrant-x86_64-unknown-linux-gnu.tar.gz"


async def install() -> dict:
    """Download the official Qdrant binary for this machine (once)."""
    if _qdrant_bin().exists():
        return {"installed": True, "path": str(_qdrant_bin()), "already": True}
    asset = _asset_name()
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        rel = await client.get("https://api.github.com/repos/qdrant/qdrant/releases/latest")
        rel.raise_for_status()
        url = next((a["browser_download_url"] for a in rel.json().get("assets", [])
                    if a["name"] == asset), None)
        if not url:
            raise RuntimeError(f"no Qdrant release asset for this platform ({asset})")
        log.info("downloading qdrant: %s", url)
        archive = _bin_dir() / asset
        async with client.stream("GET", url, timeout=600) as resp:
            resp.raise_for_status()
            with open(archive, "wb") as f:
                async for chunk in resp.aiter_bytes(1 << 20):
                    f.write(chunk)
    if asset.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(_bin_dir())
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(_bin_dir())
    archive.unlink(missing_ok=True)
    # the archive may contain the binary at root or in a subdir — locate it
    if not _qdrant_bin().exists():
        found = next((p for p in _bin_dir().rglob("qdrant*") if p.is_file() and p.stat().st_size > 1 << 20), None)
        if found and found != _qdrant_bin():
            found.rename(_qdrant_bin())
    _qdrant_bin().chmod(0o755)
    return {"installed": True, "path": str(_qdrant_bin()),
            "size_mb": round(_qdrant_bin().stat().st_size / 1048576, 1)}


async def _port_up() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            return (await client.get(f"http://localhost:{QDRANT_PORT}/collections")).status_code == 200
    except httpx.HTTPError:
        return False


async def start() -> dict:
    """Run the embedded Qdrant (storage under <workspace>/qdrant-native)."""
    global _proc
    if await _port_up():
        return {"running": True, "already": True}
    if not _qdrant_bin().exists():
        raise RuntimeError("qdrant not installed — install it first")
    storage = (get_settings().devfoundry_workspace / "qdrant-native").resolve()
    storage.mkdir(parents=True, exist_ok=True)
    _proc = subprocess.Popen(
        [str(_qdrant_bin())],
        cwd=storage,
        env={"QDRANT__SERVICE__HTTP_PORT": str(QDRANT_PORT),
             "QDRANT__STORAGE__STORAGE_PATH": str(storage / "storage"),
             "QDRANT__TELEMETRY_DISABLED": "true",
             "PATH": "/usr/bin:/bin"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        await asyncio.sleep(1)
        if await _port_up():
            return {"running": True, "pid": _proc.pid}
    raise RuntimeError("embedded qdrant did not become ready in 30s")


def stop() -> dict:
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
        _proc = None
        return {"running": False}
    return {"running": False, "already": True}


async def status() -> dict:
    return {"installed": _qdrant_bin().exists(),
            "running": await _port_up(),
            "managed": _proc is not None and _proc.poll() is None,
            "binary": str(_qdrant_bin()) if _qdrant_bin().exists() else None}


async def autostart() -> None:
    """On backend startup: if the binary is installed and nothing serves the port, run it."""
    try:
        if _qdrant_bin().exists() and not await _port_up():
            await start()
            log.info("embedded qdrant autostarted")
    except Exception:  # noqa: BLE001 — RAG falls back gracefully without it
        log.exception("embedded qdrant autostart failed")
