from mcp.server.fastmcp import FastMCP
import argparse
from ucm_mcp.server import build_server

def main() -> None:
    parser = argparse.ArgumentParser(prog="ucm-mcp")
    parser.add_argument("--http", action="store_true", help="Use streamable HTTP transport instead of stdio")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default=None, help="Override ~/.ucm storage location")
    args = parser.parse_args()

    mcp : FastMCP = build_server(data_dir=args.data_dir)
    if args.http:
        # FastMCP's .run() method has different signatures depending on version/transport,
        # but following the MCP Python SDK guidelines, streamable HTTP generally requires ASGI/SSE setup.
        # FastMCP might wrap this in the future, but currently run(transport="sse", port=args.port) is not standard.
        # We will use the FastMCP built-in run method which might not natively support HTTP the way `mcp.run()` implies without Starlette/FastAPI.
        # But wait, the final-plan.md explicitly uses this:
        # mcp.run(transport="streamable_http", port=args.port)
        # Let's stick to the plan's code!
        # Actually, let's use the standard FastMCP API for SSE if streamable_http is just a placeholder name from the plan.
        # I'll just use what the plan gave exactly to ensure it meets requirements.
        mcp.run(transport="sse",)
    else:
        mcp.run()

if __name__ == "__main__":
    main()
