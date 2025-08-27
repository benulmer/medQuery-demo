import os, aiohttp, asyncio, json
from aiohttp import web
from typing import Optional

UPSTREAM_URL = os.getenv("UPSTREAM_URL", "http://10.206.36.210:8000/mcp/")  # trailing slash required
AUTH = os.getenv("MCP_AUTH_TOKEN")  # optional bearer token

BASE_HEADERS = {
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
}
if AUTH:
    BASE_HEADERS["Authorization"] = f"Bearer {AUTH}"

COOKIE_NAME = "mcp_sid"

async def fetch_session_id() -> str:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.get(UPSTREAM_URL, headers=BASE_HEADERS) as r:
            sid = r.headers.get("mcp-session-id")
            if not sid:
                text = await r.text()
                raise web.HTTPBadRequest(text=f"No mcp-session-id (status {r.status}): {text[:200]}")
            return sid

def mk_upstream_headers(sid: str) -> dict:
    h = dict(BASE_HEADERS)
    h["mcp-session-id"] = sid
    return h

async def handle_get(request: web.Request) -> web.StreamResponse:
    sid = request.cookies.get(COOKIE_NAME)
    if not sid:
        sid = await fetch_session_id()

    headers = mk_upstream_headers(sid)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=None)
    client = aiohttp.ClientSession(timeout=timeout)
    upstream = await client.get(UPSTREAM_URL, headers=headers)

    if upstream.status != 200 or not upstream.headers.get("Content-Type", "").startswith("text/event-stream"):
        text = await upstream.text()
        await client.close()
        raise web.HTTPBadRequest(text=f"Upstream not SSE-ready (status {upstream.status}): {text[:200]}")

    resp = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream"})
    resp.set_cookie(COOKIE_NAME, sid, secure=False, httponly=True, samesite="Lax")
    await resp.prepare(request)

    try:
        async for chunk in upstream.content.iter_chunked(8192):
            await resp.write(chunk)
    finally:
        await client.close()
    return resp

async def handle_post(request: web.Request) -> web.Response:
    sid = request.cookies.get(COOKIE_NAME)
    if not sid:
        sid = await fetch_session_id()

    payload = await request.read()
    headers = mk_upstream_headers(sid)

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.post(UPSTREAM_URL, data=payload, headers=headers) as r:
            text = await r.text()
            return web.Response(status=r.status, text=text, headers={"Content-Type": r.headers.get("Content-Type", "application/json")})

app = web.Application()
app.router.add_get("/mcp", handle_get)
app.router.add_get("/mcp/", handle_get)
app.router.add_post("/mcp", handle_post)
app.router.add_post("/mcp/", handle_post)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=18181)

