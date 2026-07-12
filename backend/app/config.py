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
