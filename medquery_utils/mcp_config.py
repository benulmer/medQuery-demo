from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple


def load_mcp_from_config(config_path: str = "mcp.config.json") -> Optional[Tuple[str, Dict[str, str]]]:
    """Load MCP base URL and headers from a JSON config file.

    The config shape is expected to be:
    {
      "mcpServers": {
        "name": { "url": "http://host:port/mcp", "headers": {"...": "..."} }
      },
      "defaultServer": "name"
    }

    Environment overrides:
    - MCP_CONFIG_PATH: alternate path to config file
    - MCP_SERVER: server key to use (overrides defaultServer)
    - MCP_SESSION_ID: if set, inject as header 'MCP-Session-Id'
    - MCP_HEADERS: JSON string to merge/override headers
    """

    path = os.getenv("MCP_CONFIG_PATH", config_path)
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    servers = data.get("mcpServers") or {}
    if not servers:
        return None

    server_name = os.getenv("MCP_SERVER") or data.get("defaultServer")
    if server_name and server_name in servers:
        server = servers[server_name]
    else:
        # pick the first defined server
        first_key = next(iter(servers.keys()))
        server = servers[first_key]

    base_url = server.get("url")
    headers: Dict[str, str] = dict(server.get("headers") or {})

    # Inject session header from env if provided
    session_id = os.getenv("MCP_SESSION_ID")
    if session_id and "MCP-Session-Id" not in headers:
        headers["MCP-Session-Id"] = session_id

    # Merge arbitrary headers from env JSON
    hdr_json = os.getenv("MCP_HEADERS")
    if hdr_json:
        try:
            headers.update(json.loads(hdr_json))
        except Exception:
            pass

    if not base_url:
        return None

    return base_url, headers

