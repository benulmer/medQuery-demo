import asyncio, aiohttp, os
from mcp import ClientSession
from mcp.client.sse import sse_client

URL = "http://10.206.36.210:8000/mcp/"  # trailing slash required
BASE_HEADERS = {"Accept":"text/event-stream","Content-Type":"application/json"}

async def fetch_session_id() -> str:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.get(URL, headers=BASE_HEADERS) as r:
            sid = r.headers.get("mcp-session-id")
            if not sid:
                text = await r.text()
                raise RuntimeError(f"No mcp-session-id (status {r.status}): {text[:200]}")
            return sid

async def main():
    os.environ.setdefault("AIOHTTP_NO_EXTENSIONS","1")
    sid = await fetch_session_id()
    headers = {**BASE_HEADERS, "mcp-session-id": sid}
    async with sse_client(URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Remote tools:", [t.name for t in tools.tools])

if __name__ == "__main__":
    asyncio.run(main())

