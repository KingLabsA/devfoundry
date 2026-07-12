import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.mcp import client, registry
from app.orchestrator.deploy_providers import available_providers

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class ServerConfig(BaseModel):
    name: str
    transport: str = "stdio"          # "stdio" | "http"
    command: str = ""                 # stdio
    args: list[str] = []              # stdio
    env: dict[str, str] = {}          # stdio
    url: str = ""                     # http
    headers: dict[str, str] = {}      # http


class ToolCall(BaseModel):
    tool: str
    arguments: dict = {}


@router.get("/mcp/servers")
async def list_servers() -> list[dict]:
    servers = registry.load_servers()

    async def probe(name: str, cfg: dict) -> dict:
        try:
            tools = await asyncio.wait_for(client.list_tools(cfg), timeout=20)
            return {"name": name, **cfg, "status": "connected", "tools": len(tools)}
        except Exception as exc:  # noqa: BLE001 — status probe must never 500
            return {"name": name, **cfg, "status": "error", "error": str(exc)[:200], "tools": 0}

    return await asyncio.gather(*(probe(n, c) for n, c in servers.items()))


@router.post("/mcp/servers", status_code=201)
async def add_server(cfg: ServerConfig) -> dict:
    if cfg.transport == "http" and not cfg.url:
        raise HTTPException(422, "http transport requires a url")
    if cfg.transport == "stdio" and not cfg.command:
        raise HTTPException(422, "stdio transport requires a command")
    entry = {"transport": cfg.transport}
    if cfg.transport == "http":
        entry.update({"url": cfg.url, **({"headers": cfg.headers} if cfg.headers else {})})
    else:
        entry.update({"command": cfg.command, "args": cfg.args, **({"env": cfg.env} if cfg.env else {})})
    registry.add_server(cfg.name, entry)
    return {"name": cfg.name, **entry}


@router.delete("/mcp/servers/{name}")
async def delete_server(name: str) -> dict:
    if not registry.remove_server(name):
        raise HTTPException(404, "server not found")
    return {"removed": name}


@router.get("/mcp/servers/{name}/tools")
async def server_tools(name: str) -> list[dict]:
    cfg = registry.load_servers().get(name)
    if cfg is None:
        raise HTTPException(404, "server not found")
    try:
        return await client.list_tools(cfg)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"could not reach MCP server: {exc}")


@router.post("/mcp/servers/{name}/call")
async def call_server_tool(name: str, body: ToolCall) -> dict:
    cfg = registry.load_servers().get(name)
    if cfg is None:
        raise HTTPException(404, "server not found")
    try:
        return {"result": await client.call_tool(cfg, body.tool, body.arguments)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"tool call failed: {exc}")


@router.get("/deploy/providers")
async def deploy_providers() -> list[dict]:
    return available_providers()
