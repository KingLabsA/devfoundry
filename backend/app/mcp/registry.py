"""Persistent registry of user-configured MCP servers (mcp.json at project root)."""
import json
import logging
from pathlib import Path

from app.config import get_settings

log = logging.getLogger(__name__)


def _config_path() -> Path:
    return get_settings().devfoundry_workspace.resolve().parent / "mcp.json"


def load_servers() -> dict[str, dict]:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()).get("mcpServers", {})
    except (json.JSONDecodeError, OSError) as exc:
        log.error("cannot read %s: %s", path, exc)
        return {}


def save_servers(servers: dict[str, dict]) -> None:
    _config_path().write_text(json.dumps({"mcpServers": servers}, indent=2))


def add_server(name: str, cfg: dict) -> None:
    servers = load_servers()
    servers[name] = cfg
    save_servers(servers)


def remove_server(name: str) -> bool:
    servers = load_servers()
    if name not in servers:
        return False
    del servers[name]
    save_servers(servers)
    return True
