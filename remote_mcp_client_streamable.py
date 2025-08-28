import asyncio, os
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import aiohttp


URL = "http://10.206.36.210:8000/mcp/"  # trailing slash required

BASE_HEADERS = {
    # Server expects both for POST paths; fine for StreamableHTTP too
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}

AUTH = os.getenv("MCP_AUTH_TOKEN")
if AUTH:
    BASE_HEADERS["Authorization"] = f"Bearer {AUTH}"


async def main() -> None:
    # Prefetch session id via GET and inject into headers
    sid = None
    async with aiohttp.ClientSession() as http:
        async with http.get(URL, headers={"Accept":"text/event-stream","Content-Type":"application/json"}) as r:
            sid = r.headers.get("mcp-session-id")
            print("[prefetch] GET status=", r.status, "sid=", sid)
    headers = dict(BASE_HEADERS)
    if sid:
        headers["mcp-session-id"] = sid

    # Use Streamable HTTP transport
    async with streamablehttp_client(URL, headers=headers, sse_read_timeout=60) as (read, write, get_sid):
        sid = get_sid()  # May be None until first exchange
        print("[streamable] session id (pre-init):", sid)

        async with ClientSession(read, write) as session:
            # Initialize with SDK defaults (server should negotiate protocol/capabilities)
            init_res = await session.initialize()
            print("[initialize] ->", init_res)

            # Try listing tools using SDK
            try:
                tools = await session.list_tools()
                names = [t.name for t in tools.tools]
                print("[tools/list] ->", names)
            except Exception as e:
                print("[tools/list] ERROR:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())

