import asyncio
from mcp_client_local import call_tool


async def main():
    print("cohort_stats (asthma):")
    print(await call_tool("patient_aggregate", {"conditions": ["Asthma"]}))

    print("patient_summary (intern):")
    print(await call_tool("patient_get", {"id": "P001"}))

    print("patient_summary (doctor):")
    print(await call_tool("patient_get", {"id": "P001"}))


if __name__ == "__main__":
    asyncio.run(main())

