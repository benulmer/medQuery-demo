from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastmcp import Client
from mcp import ClientSession as MCPClientSession
from mcp.client.streamable_http import streamablehttp_client
import aiohttp
from medquery_utils.mcp_config import load_mcp_from_config


class FastMCPBridge:
    """Thin wrapper over fastmcp.Client for calling MedQuery tools.

    Supported modes:
    - stdio: spawn local server process
    - sse: connect to remote SSE endpoint (no custom headers)
    - stream: connect to remote Streamable HTTP endpoint (supports headers)
    """

    def __init__(self, mode: str = "stream", command: Optional[List[str]] = None, url: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> None:
        self.mode = (mode or "stdio").lower()
        self.command = command
        self.url = url
        self.headers: Dict[str, str] = headers or {}

    @staticmethod
    def initialize_from_env() -> Optional["FastMCPBridge"]:
        mode = os.getenv("FASTMCP_MODE", "stream").lower()
        if mode == "stdio":
            cmd_str = os.getenv("FASTMCP_COMMAND", "mcp_stdio_server.py").strip()
            # naive split is fine for simple commands
            command = cmd_str.split()
            return FastMCPBridge(mode="stdio", command=command)
        elif mode in ("sse", "http", "stream"):
            # Prefer config file if present
            cfg = load_mcp_from_config()
            headers: Dict[str, str] = {}
            url = None
            if cfg:
                url, headers = cfg[0], dict(cfg[1])
            # Env overrides
            url = os.getenv("FASTMCP_URL") or os.getenv("MCP_URL") or url
            hdr_json = os.getenv("MCP_HEADERS")
            if hdr_json:
                import json
                try:
                    headers.update(json.loads(hdr_json))
                except Exception:
                    pass
            if not url:
                return None
            # Ensure Accept header compatible with server
            headers.setdefault("Accept", "application/json, text/event-stream")
            headers.setdefault("Content-Type", "application/json")
            return FastMCPBridge(mode=("stream" if mode != "sse" else "sse"), url=url, headers=headers)
        return None

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if self.mode == "stdio":
            if not self.command:
                raise RuntimeError("FASTMCP stdio command not configured")
            # Client prefers a script path string; if user provided 'python server.py', use the script
            cmd_list = self.command if isinstance(self.command, list) else str(self.command).split()
            script = cmd_list[-1]
            async with Client(script) as client:
                result = await client.call_tool(tool_name, params)
                return getattr(result, "data", result)
        elif self.mode == "sse":
            if not self.url:
                raise RuntimeError("FASTMCP URL not configured for SSE mode")
            # fastmcp.Client does not accept custom headers; use a local proxy to inject them
            async with Client(self.url) as client:
                result = await client.call_tool(tool_name, params)
                return getattr(result, "data", result)
        elif self.mode == "stream":
            if not self.url:
                raise RuntimeError("FASTMCP URL not configured for stream mode")
            # Prefetch session id and inject into headers
            session_id: Optional[str] = None
            async with aiohttp.ClientSession() as http:
                async with http.get(self.url, headers={"Accept": "text/event-stream", "Content-Type": "application/json"}) as r:
                    session_id = r.headers.get("mcp-session-id")
            headers = dict(self.headers)
            if session_id:
                headers["mcp-session-id"] = session_id
            async with streamablehttp_client(self.url, headers=headers) as (read, write, _get_sid):
                async with MCPClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=params)
                    return getattr(result, "data", result)
        raise RuntimeError(f"Unsupported FASTMCP mode: {self.mode}")

