import asyncio
from ucm_mcp.server import build_server
mcp = build_server()
async def main():
    print(await mcp.call_tool('ucm_list_projects', {}))
asyncio.run(main())
