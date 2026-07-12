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
    return os.environ.get(key, default)
