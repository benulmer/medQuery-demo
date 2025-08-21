#!/usr/bin/env python3
"""
Tiny reverse proxy to forward MCP SSE/HTTP to a remote server while injecting
required headers (e.g., MCP-Session-Id). This lets fastmcp.Client connect to
http://localhost:<port>/mcp while the proxy adds headers and forwards to the
remote MCP at REMOTE_URL.

Usage:
  export REMOTE_URL=http://10.206.36.210:8000/mcp
  export PROXY_PORT=18181
  export SESSION_HEADER="MCP-Session-Id"
  export SESSION_VALUE="<YOUR_SESSION_ID>"
  python mcp_sse_proxy.py

Then point FASTMCP_URL at http://localhost:18181/mcp
"""

from __future__ import annotations

import os
from typing import Dict

import requests
from flask import Flask, request, Response
from medquery_utils.mcp_config import load_mcp_from_config
from werkzeug.serving import WSGIRequestHandler


_cfg = load_mcp_from_config() or (None, {})
_cfg_url, _cfg_headers = _cfg if _cfg else (None, {})
REMOTE_URL = (os.getenv("REMOTE_URL") or _cfg_url or "http://10.206.36.210:8000/mcp").rstrip("/")
PROXY_PORT = int(os.getenv("PROXY_PORT", "18181"))
SESSION_HEADER = os.getenv("SESSION_HEADER") or next((k for k in _cfg_headers.keys() if k.lower().endswith("session-id")), "MCP-Session-Id")
SESSION_VALUE = os.getenv("SESSION_VALUE") or _cfg_headers.get(SESSION_HEADER, "")

app = Flask(__name__)
WSGIRequestHandler.protocol_version = "HTTP/1.1"


def _inject_headers(incoming: Dict[str, str]) -> Dict[str, str]:
    headers = {k: v for k, v in incoming.items() if k.lower() not in {"host"}}
    # Enforce required headers
    headers.setdefault("Accept", "text/event-stream")
    if SESSION_VALUE:
        headers[SESSION_HEADER] = SESSION_VALUE
    return headers


@app.route("/mcp", methods=["GET", "POST"])
def mcp_root() -> Response:
    # Pass-through root to remote; many clients probe this
    url = f"{REMOTE_URL}"
    headers = _inject_headers(dict(request.headers))
    if request.method == "GET":
        r = requests.get(url, headers=headers, stream=True)
    else:
        r = requests.post(url, headers=headers, data=request.get_data(), stream=True)
    return Response(r.iter_content(chunk_size=None), status=r.status_code, headers=dict(r.headers))


@app.route("/mcp/health", methods=["GET"])
def health() -> Response:
    r = requests.get(f"{REMOTE_URL}/health", headers=_inject_headers(dict(request.headers)), stream=True)
    return Response(r.iter_content(chunk_size=None), status=r.status_code, headers=dict(r.headers))


@app.route("/mcp/tools", methods=["GET"])
def tools() -> Response:
    r = requests.get(f"{REMOTE_URL}/tools", headers=_inject_headers(dict(request.headers)), stream=True)
    return Response(r.iter_content(chunk_size=None), status=r.status_code, headers=dict(r.headers))


@app.route("/mcp/<path:path>", methods=["GET", "POST"])
def passthrough(path: str) -> Response:
    url = f"{REMOTE_URL}/{path}"
    headers = _inject_headers(dict(request.headers))
    if request.method == "GET":
        r = requests.get(url, headers=headers, stream=True)
    else:
        r = requests.post(url, headers=headers, data=request.get_data(), stream=True)
    return Response(r.iter_content(chunk_size=None), status=r.status_code, headers=dict(r.headers))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PROXY_PORT, debug=False, threaded=True)

