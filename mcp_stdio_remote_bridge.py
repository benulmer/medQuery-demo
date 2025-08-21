#!/usr/bin/env python3
"""
FastMCP stdio bridge to a remote MCP HTTP server.

It exposes the same tools (patient_search, patient_get, patient_aggregate)
but forwards each call to the remote server using requests, with headers
loaded from mcp.config.json or env.

Env/config:
- Reads URL and headers from medquery_utils.mcp_config.load_mcp_from_config()
- Fallback env:
  - FASTMCP_REMOTE_URL (e.g., http://host:8000/mcp)
  - FASTMCP_REMOTE_HEADERS (JSON string)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests
from fastmcp import FastMCP

from medquery_utils.mcp_config import load_mcp_from_config


def _load_remote() -> tuple[str, Dict[str, str]]:
    cfg = load_mcp_from_config() or (None, {})
    base_url = cfg[0] if cfg else None
    headers: Dict[str, str] = dict(cfg[1]) if cfg else {}
    # Fallbacks/overrides from env
    base_url = os.getenv("FASTMCP_REMOTE_URL", base_url)
    hdr_json = os.getenv("FASTMCP_REMOTE_HEADERS")
    if hdr_json:
        try:
            headers.update(json.loads(hdr_json))
        except Exception:
            pass
    headers.setdefault("Accept", "text/event-stream")
    if not base_url:
        raise RuntimeError("Remote MCP base URL not configured (see mcp.config.json or FASTMCP_REMOTE_URL)")
    return base_url.rstrip("/"), headers


mcp = FastMCP("MedQuery-RemoteBridge", stateless_http=True)

REMOTE_URL, REMOTE_HEADERS = _load_remote()


def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{REMOTE_URL}{path}"
    # For tool POSTs, prefer JSON accept/content negotiation
    headers = dict(REMOTE_HEADERS)
    headers.setdefault("Content-Type", "application/json")
    # Preserve remote's expected Accept (often text/event-stream)
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def patient_search(
    min_age: Optional[int] = None,
    conditions: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    payload: Dict[str, Any] = {
        "min_age": min_age,
        "conditions": conditions,
        "limit": limit,
        "offset": offset,
    }
    data = _post("/tool/patient_search", payload)
    return data.get("results", [])


@mcp.tool()
def patient_get(id: Optional[str] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {"id": id, "name": name}
    data = _post("/tool/patient_get", payload)
    return data.get("result")


@mcp.tool()
def patient_aggregate(
    min_age: Optional[int] = None,
    conditions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    payload: Dict[str, Any] = {"min_age": min_age, "conditions": conditions}
    data = _post("/tool/patient_aggregate", payload)
    return data.get("results", [])


if __name__ == "__main__":
    # Run as stdio server
    mcp.run()

