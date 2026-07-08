import asyncio
from ucm_mcp.server import build_server

async def main():
    mcp = build_server()
    tools = await mcp._list_tools()
    if tools:
        t = tools[0]
        print("FN:", getattr(t, 'fn', None))

asyncio.run(main())
