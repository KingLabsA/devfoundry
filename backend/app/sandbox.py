"""OS-level sandbox for executing GENERATED code (npm install/build/test, pytest).

LLM-generated code must not run with full user privileges. When enabled (default),
project commands are wrapped so file WRITES are confined to the project directory
plus the caches the toolchain needs; reads and network stay allowed (npm/pip need
them). This blocks the classic risk: generated code (or a malicious postinstall
script) overwriting files elsewhere on the machine.

Backends:
- macOS:  sandbox-exec with a deny-file-write* profile (project/tmp/caches allowed)
- Linux:  bubblewrap (bwrap) with / read-only and the project bound read-write
- else / SANDBOX=0: passthrough (logged once)

Honest scope: this is a write-confinement sandbox, not full isolation — network
and reads are permitted by design so builds work.
"""
import logging
import os
import platform
import shutil
from pathlib import Path

from app.config import env_value

log = logging.getLogger(__name__)
_warned = {"done": False}


def enabled() -> bool:
    return (env_value("SANDBOX") or "1").strip() not in ("0", "false", "off")


def _mac_profile(project: Path) -> str:
    home = Path.home()
    allow = [project.resolve(), Path("/tmp"), Path("/private/tmp"),
             Path("/private/var/folders"), Path("/dev"),
             home / ".npm", home / ".cache", home / "Library/Caches"]
    allow_rules = "\n".join(f'  (subpath "{p}")' for p in allow)
    return (
        "(version 1)\n"
        "(allow default)\n"
        "(deny file-write*)\n"
        f"(allow file-write*\n{allow_rules}\n)"
    )


def wrap(args: list[str], project: Path) -> list[str]:
    """Wrap a command so its writes are confined to the project (+ caches)."""
    if not enabled():
        if not _warned["done"]:
            log.warning("SANDBOX=0 — generated code runs unconfined")
            _warned["done"] = True
        return args

    system = platform.system()
    if system == "Darwin" and shutil.which("sandbox-exec"):
        return ["sandbox-exec", "-p", _mac_profile(project)] + args
    if system == "Linux" and shutil.which("bwrap"):
        home = str(Path.home())
        return ["bwrap", "--ro-bind", "/", "/",
                "--bind", str(project.resolve()), str(project.resolve()),
                "--bind", "/tmp", "/tmp",
                "--bind", f"{home}/.npm", f"{home}/.npm",
                "--bind", f"{home}/.cache", f"{home}/.cache",
                "--dev", "/dev", "--proc", "/proc",
                "--die-with-parent"] + args
    if not _warned["done"]:
        log.warning("no sandbox backend on %s — generated code runs unconfined", system)
        _warned["done"] = True
    return args


def status() -> dict:
    system = platform.system()
    backend = ("sandbox-exec" if system == "Darwin" and shutil.which("sandbox-exec")
               else "bwrap" if system == "Linux" and shutil.which("bwrap")
               else None)
    return {"enabled": enabled(), "backend": backend, "os": system,
            "confines": "file writes → project dir + toolchain caches",
            "allows": "reads + network (builds need them)"}
