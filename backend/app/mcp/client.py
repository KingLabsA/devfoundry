"""Minimal MCP (Model Context Protocol) client.

Supports the two standard transports:
- stdio: spawn the server command, newline-delimited JSON-RPC
- http:  streamable HTTP (JSON or SSE-encoded responses)
"""
import asyncio
import json
import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "devfoundry", "version": "0.1.0"}


class MCPError(RuntimeError):
    pass


def _init_request(rpc_id: int) -> dict:
    return {
        "jsonrpc": "2.0", "id": rpc_id, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO},
    }


class StdioTransport:
    """One short-lived session per operation: spawn, initialize, request, close."""

    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None):
        self.command = command
        self.args = args
        self.env = env or {}

    async def request(self, method: str, params: dict | None = None, timeout: int = 30) -> Any:
        proc = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env={**os.environ, **self.env},
        )

        async def send(msg: dict) -> None:
            proc.stdin.write((json.dumps(msg) + "\n").encode())
            await proc.stdin.drain()

        async def recv(want_id: int) -> dict:
            while True:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
                if not line:
                    raise MCPError("server closed the pipe")
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("id") == want_id:
                    return msg

        try:
            await send(_init_request(1))
            init = await recv(1)
            if "error" in init:
                raise MCPError(f"initialize failed: {init['error']}")
            await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            await send({"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}})
            resp = await recv(2)
            if "error" in resp:
                raise MCPError(str(resp["error"]))
            return resp.get("result")
        except asyncio.TimeoutError:
            raise MCPError(f"{self.command}: timed out after {timeout}s")
        finally:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass


class HttpTransport:
    def __init__(self, url: str, headers: dict[str, str] | None = None):
        self.url = url
        self.headers = headers or {}

    @staticmethod
    def _parse(resp: httpx.Response) -> dict:
        ctype = resp.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            raise MCPError("empty SSE response")
        return resp.json()

    async def request(self, method: str, params: dict | None = None, timeout: int = 30) -> Any:
        headers = {"Accept": "application/json, text/event-stream",
                   "Content-Type": "application/json", **self.headers}
        async with httpx.AsyncClient(timeout=timeout) as client:
            init = await client.post(self.url, headers=headers, json=_init_request(1))
            init.raise_for_status()
            session = init.headers.get("mcp-session-id")
            if session:
                headers["mcp-session-id"] = session
            await client.post(self.url, headers=headers,
                              json={"jsonrpc": "2.0", "method": "notifications/initialized"})
            resp = await client.post(self.url, headers=headers,
                                     json={"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}})
            resp.raise_for_status()
            msg = self._parse(resp)
            if "error" in msg:
                raise MCPError(str(msg["error"]))
            return msg.get("result")


def make_transport(cfg: dict) -> StdioTransport | HttpTransport:
    if cfg.get("transport") == "http":
        return HttpTransport(cfg["url"], cfg.get("headers"))
    return StdioTransport(cfg["command"], cfg.get("args", []), cfg.get("env"))


async def list_tools(cfg: dict) -> list[dict]:
    result = await make_transport(cfg).request("tools/list")
    return (result or {}).get("tools", [])


async def call_tool(cfg: dict, name: str, arguments: dict) -> Any:
    return await make_transport(cfg).request("tools/call", {"name": name, "arguments": arguments}, timeout=120)
