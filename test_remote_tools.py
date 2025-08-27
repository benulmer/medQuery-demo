import asyncio
from remote_mcp_client import list_remote_tools, call_remote_tool


async def main():
    tools = await list_remote_tools()
    print("Remote tools:", tools)

    # Example (commented): adjust tool/args to match remote
    # res = await call_remote_tool("patient_aggregate", {"conditions": ["Asthma"]})
    # print("patient_aggregate:", res)


if __name__ == "__main__":
    asyncio.run(main())

