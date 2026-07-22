"""Embedded native services — no Docker required.

Qdrant ships official single-binary releases; DevFoundry downloads the right one
for this OS/arch once (into <workspace>/bin), then runs and supervises it as a
child process. This replaces the Docker container for vector-store RAG.

The FreeLLMAPI gateway is a Docker service; DevFoundry manages its lifecycle
(status / start / stop / autostart) so the app never depends on the user
running docker commands by hand.
"""
import asyncio
import logging
import platform
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import httpx

from app.config import env_value, get_settings

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


# ---------------------------------------------------------------- FreeLLMAPI gateway
def _gateway_url() -> str:
    return env_value("FREELLMAPI_URL") or "http://localhost:3002"


def _run(args: list[str], timeout: int = 10, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)


async def _url_up(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            return (await client.get(url)).status_code < 500
    except httpx.HTTPError:
        return False


async def _daemon_up() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        r = await asyncio.to_thread(_run, [docker, "info", "--format", "{{.ServerVersion}}"], 6)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _gateway_container() -> tuple[str | None, str | None]:
    """(name, state) of a freellmapi container — running or stopped — if one exists."""
    docker = shutil.which("docker")
    if not docker:
        return None, None
    try:
        out = _run([docker, "ps", "-a", "--format", "{{.Names}}\t{{.State}}"], 10)
    except subprocess.TimeoutExpired:
        return None, None
    for line in out.stdout.splitlines():
        name, _, state = line.partition("\t")
        if "freellmapi" in name.lower():
            return name, state.strip()
    return None, None


def _compose_dir() -> Path | None:
    """Where the FreeLLMAPI compose project lives (FREELLMAPI_DIR overrides)."""
    candidates = [env_value("FREELLMAPI_DIR"), "~/freellmapi", "~/Documents/freellmapi"]
    for cand in candidates:
        if not cand:
            continue
        p = Path(cand).expanduser()
        if any((p / f).exists() for f in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml")):
            return p
    return None


def _daemon_launchable() -> bool:
    return platform.system() == "Darwin" and Path("/Applications/Docker.app").exists()


async def freellmapi_status() -> dict:
    """Rich gateway state so the UI can offer exactly the right action."""
    url = _gateway_url()
    up = await _url_up(url)
    docker_cli = shutil.which("docker") is not None
    daemon = await _daemon_up() if docker_cli else False
    name = state = None
    if daemon:
        name, state = await asyncio.to_thread(_gateway_container)
    comp = _compose_dir()
    startable = docker_cli and (daemon or _daemon_launchable()) and bool(name or comp)
    return {"up": up, "url": url, "docker_cli": docker_cli, "docker_daemon": daemon,
            "container": name, "container_state": state,
            "compose_dir": str(comp) if comp else None, "startable": startable}


async def freellmapi_start() -> dict:
    """One-click gateway start: launch Docker if needed (macOS), then the container."""
    url = _gateway_url()
    if await _url_up(url):
        return {"up": True, "url": url, "already": True}
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("docker CLI not found — FreeLLMAPI runs as a Docker service. "
                           "Install Docker Desktop, or point FREELLMAPI_URL at a remote gateway.")
    if not await _daemon_up():
        if not _daemon_launchable():
            raise RuntimeError("Docker daemon is not running — start Docker, then retry.")
        log.info("launching Docker Desktop for the gateway")
        await asyncio.to_thread(_run, ["open", "-a", "Docker"], 15)
        for _ in range(45):
            await asyncio.sleep(2)
            if await _daemon_up():
                break
        else:
            raise RuntimeError("Docker daemon did not come up within 90s")
    name, _state = await asyncio.to_thread(_gateway_container)
    if name:
        r = await asyncio.to_thread(_run, [docker, "start", name], 60)
        if r.returncode != 0:
            raise RuntimeError(f"docker start {name} failed: {r.stderr[-300:]}")
    else:
        comp = _compose_dir()
        if not comp:
            raise RuntimeError("no FreeLLMAPI install found — git clone "
                               "https://github.com/tashfeenahmed/freellmapi && docker compose up -d "
                               "(or set FREELLMAPI_DIR to where its docker-compose.yml lives)")
        r = await asyncio.to_thread(_run, [docker, "compose", "up", "-d"], 300, str(comp))
        if r.returncode != 0:
            raise RuntimeError(f"docker compose up failed: {r.stderr[-300:]}")
    for _ in range(30):
        await asyncio.sleep(1)
        if await _url_up(url):
            return {"up": True, "url": url, "container": name}
    raise RuntimeError("gateway container started but the port did not answer within 30s")


async def freellmapi_stop() -> dict:
    docker = shutil.which("docker")
    if not docker or not await _daemon_up():
        return {"up": False, "already": True}
    name, state = await asyncio.to_thread(_gateway_container)
    if name and state == "running":
        await asyncio.to_thread(_run, [docker, "stop", name], 60)
        return {"up": False, "stopped": name}
    return {"up": False, "already": True}


async def gateway_autostart() -> None:
    """On backend startup: if Docker is already running and the freellmapi container
    exists but is stopped, start it. Never launches Docker Desktop itself — that
    heavier path stays behind the explicit Start button on the Gateway page."""
    try:
        if await _url_up(_gateway_url()):
            return
        docker = shutil.which("docker")
        if not docker or not await _daemon_up():
            return
        name, state = await asyncio.to_thread(_gateway_container)
        if name and state != "running":
            await asyncio.to_thread(_run, [docker, "start", name], 60)
            log.info("freellmapi gateway autostarted (%s)", name)
    except Exception:  # noqa: BLE001 — the provider chain falls back gracefully without it
        log.exception("freellmapi gateway autostart failed")
