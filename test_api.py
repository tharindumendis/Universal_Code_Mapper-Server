import asyncio
from fastapi import FastAPI
from fastmcp import FastMCP
from ucm_mcp.server import build_server

mcp = build_server()
print("Tools:", [t.name for t in mcp._list_tools()])
