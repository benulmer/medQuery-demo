import asyncio, aiohttp, os
from typing import Any
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_URL = "http://10.206.36.210:8000/mcp/"  # trailing slash required
BASE_HEADERS = {
    # Accept both to satisfy server's POST requirements
    "Accept":"application/json, text/event-stream",
    "Content-Type":"application/json",
    # "Authorization": f"Bearer {os.getenv('MCP_AUTH_TOKEN')}"  # uncomment if needed
}


async def _fetch_session_id() -> str:
    async with aiohttp.ClientSession() as http:
        async with http.get(MCP_URL, headers=BASE_HEADERS) as r:
            sid = r.headers.get("mcp-session-id")
            if not sid:
                text = await r.text()
                raise RuntimeError(f"No mcp-session-id (status={r.status}): {text[:200]}")
            return sid


async def call_remote_tool(name: str, args: dict[str, Any]) -> Any:
    sid = await _fetch_session_id()
    headers = {**BASE_HEADERS, "mcp-session-id": sid}
    async with sse_client(MCP_URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(name, arguments=args)


async def list_remote_tools() -> list[str]:
    sid = await _fetch_session_id()
    headers = {**BASE_HEADERS, "mcp-session-id": sid}
    async with sse_client(MCP_URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [t.name for t in tools.tools]

if __name__ == "__main__":
    async def main():
        print("Remote tools:", await list_remote_tools())
    asyncio.run(main())

