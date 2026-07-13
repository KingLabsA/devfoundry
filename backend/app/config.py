from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    metagpt_url: str = "http://localhost:9101"
    boltdiy_url: str = "http://localhost:9102"
    opencode_url: str = "http://localhost:9103"
    orc_url: str = "http://localhost:9104"
    superpowers_url: str = "http://localhost:9105"

    devfoundry_host: str = "0.0.0.0"
    devfoundry_port: int = 9100
    devfoundry_workspace: Path = Path("./workspace")
    devfoundry_log_level: str = "INFO"
    devfoundry_mock: bool = False
    devfoundry_embedded: bool = True  # run all stages in-process (no Docker sidecars)
    service_timeout_seconds: int = 600

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.devfoundry_workspace.mkdir(parents=True, exist_ok=True)
    return settings


_env_file_cache: dict = {"mtime": 0.0, "vars": {}}


def env_value(key: str, default: str = "") -> str:
    """Read a config value, preferring the project .env file (re-read on change)
    over process env. This lets keys saved in Settings take effect immediately,
    without restarting the orchestrator."""
    env_path = get_settings().devfoundry_workspace.resolve().parent / ".env"
    try:
        mtime = env_path.stat().st_mtime
        if mtime != _env_file_cache["mtime"]:
            parsed = {}
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    parsed[k.strip()] = v.strip()
            _env_file_cache.update(mtime=mtime, vars=parsed)
    except OSError:
        pass
    file_val = _env_file_cache["vars"].get(key, "")
    if file_val:
        return file_val
    import os
    env_val = os.environ.get(key, "")
    if env_val:
        return env_val
    # macOS Keychain fallback for secrets (kept out of plaintext .env).
    if key.endswith(("_KEY", "_TOKEN")) or key in ("HF_TOKEN", "GITHUB_TOKEN"):
        kc = _keychain_get(key)
        if kc:
            return kc
    return default


_KEYCHAIN_SERVICE = "com.devfoundry.app"
_keychain_cache: dict[str, str] = {}


def _keychain_get(key: str) -> str:
    import platform
    if platform.system() != "Darwin":
        return ""
    if key in _keychain_cache:
        return _keychain_cache[key]
    import subprocess
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", key, "-s", _KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=3)
        val = out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        val = ""
    _keychain_cache[key] = val
    return val
