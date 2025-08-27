import os, asyncio, aiohttp, json
from typing import Any, List

URL = "http://10.206.36.210:8000/mcp/"  # trailing slash required
AUTH = os.getenv("MCP_AUTH_TOKEN")

BASE_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
if AUTH:
    BASE_HEADERS["Authorization"] = f"Bearer {AUTH}"

INIT_PARAMS = {
    "protocolVersion": "2024-11-05",
    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
    "clientInfo": {"name": "post-only", "version": "0.1.0"},
}

CANDIDATES = [
    {},
    {"cursor": None},
    {"cursor": ""},
    {"limit": 50},
    {"offset": 0, "limit": 50},
    {"pagination": {"cursor": None}},
    {"pagination": {"cursor": "", "limit": 50}},
]


async def fetch_sid(session: aiohttp.ClientSession) -> str:
    async with session.get(URL, headers={"Accept":"text/event-stream","Content-Type":"application/json"}) as r:
        sid = r.headers.get("mcp-session-id")
        if not sid:
            txt = await r.text()
            raise RuntimeError(f"No mcp-session-id (status {r.status}): {txt[:200]}")
        return sid


async def mcp_post(session: aiohttp.ClientSession, sid: str, method: str, params: dict) -> dict:
    payload = {"jsonrpc":"2.0","id":method,"method":method,"params":params}
    headers = dict(BASE_HEADERS); headers["mcp-session-id"] = sid
    async with session.post(URL, headers=headers, data=json.dumps(payload)) as r:
        ctype = (r.headers.get("Content-Type") or "").lower()
        # Server may stream JSON-RPC over SSE even for POST
        if ctype.startswith("text/event-stream"):
            data_buf = []
            async for chunk in r.content:
                line = chunk.decode("utf-8", errors="ignore")
                if line.strip() == "":
                    # end of event
                    if data_buf:
                        msg = "".join(data_buf)
                        if msg.startswith("data:"):
                            msg = msg[len("data:"):].strip()
                        try:
                            return json.loads(msg)
                        except Exception:
                            pass
                        data_buf = []
                    continue
                if line.startswith("data:"):
                    data_buf.append(line)
            raise RuntimeError(f"POST {method} -> streamed SSE without JSON payload parsed")
        else:
            txt = await r.text()
            if r.status != 200:
                raise RuntimeError(f"POST {method} -> {r.status}: {txt[:300]}")
            return json.loads(txt or "{}")


async def list_tools() -> List[str]:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        sid = await fetch_sid(http)
        await mcp_post(http, sid, "initialize", INIT_PARAMS)
        # Try multiple parameter shapes to maximize compatibility
        for params in CANDIDATES:
            res = await mcp_post(http, sid, "tools/list", params)
            tools = res.get("result", {}).get("tools", [])
            if tools:
                return [t.get("name") for t in tools if isinstance(t, dict) and t.get("name")]
        return []


async def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        sid = await fetch_sid(http)
        await mcp_post(http, sid, "initialize", {"clientInfo":{"name":"post-only","version":"0.0.1"}})
        res = await mcp_post(http, sid, "tools/call", {"name": name, "arguments": arguments})
        return res.get("result")


async def list_resources_raw() -> dict:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        sid = await fetch_sid(http)
        await mcp_post(http, sid, "initialize", INIT_PARAMS)
        return await mcp_post(http, sid, "resources/list", {"cursor": None})


if __name__ == "__main__":
    async def main():
        names = await list_tools()
        print("Remote tools (POST-only):", names)
        # Example call:
        # out = await call_tool("patient_aggregate", {"conditions":["Asthma"]})
        # print("patient_aggregate:", out)
        res = await list_resources_raw()
        print("resources/list (raw):", res)
    asyncio.run(main())

