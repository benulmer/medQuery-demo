import asyncio, aiohttp, os, sys
from mcp import ClientSession
from mcp.client.sse import sse_client

URL = "http://10.206.36.210:8000/mcp/"   # trailing slash required
AUTH = os.getenv("MCP_AUTH_TOKEN")       # optional Bearer token

BASE_HEADERS = {
    # Server requires both types to be acceptable
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
if AUTH:
    BASE_HEADERS["Authorization"] = f"Bearer {AUTH}"

async def fetch_sid() -> str:
    print("[fetch_sid] GET", URL, flush=True)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.get(URL, headers=BASE_HEADERS) as r:
            print("[fetch_sid] status", r.status, flush=True)
            sid = r.headers.get("mcp-session-id")
            print("[fetch_sid] mcp-session-id:", sid, flush=True)
            if not sid:
                body = await r.text()
                raise RuntimeError(f"No mcp-session-id (status {r.status}): {body[:200]}")
            return sid

async def main():
    os.environ.setdefault("AIOHTTP_NO_EXTENSIONS", "1")
    sid = await fetch_sid()
    headers = dict(BASE_HEADERS)
    headers["mcp-session-id"] = sid
    print("[sse_client] connecting with headers:", headers, flush=True)

    async with sse_client(URL, headers=headers) as (read, write):
        print("[sse_client] connected; calling initialize()", flush=True)
        async with ClientSession(read, write) as session:
            # Using SDK initialize (parameters support depends on installed SDK)
            await session.initialize()
            
            print("[initialize] OK; listing tools…", flush=True)
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("[list_tools] ->", names, flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("ERROR:", repr(e), file=sys.stderr)
        raise

