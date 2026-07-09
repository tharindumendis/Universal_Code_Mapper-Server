import os
import sys
import argparse
import threading
import uvicorn
import asyncio

def run_uvicorn(port: int):
    # Run uvicorn with logging disabled to avoid interfering with MCP stdio
    config = uvicorn.Config(
        "ucm_mcp.main:app",
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
    )
    server = uvicorn.Server(config)
    try:
        asyncio.run(server.serve())
    except Exception:
        pass

def main() -> None:
    parser = argparse.ArgumentParser(prog="ucm-mcp")
    parser.add_argument("--http", action="store_true", help="Use streamable HTTP transport instead of stdio")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default=None, help="Override ~/.ucm storage location")
    args = parser.parse_args()

    # Set env vars before importing main
    if args.data_dir:
        os.environ["UCM_DATA_DIR"] = args.data_dir
    os.environ["UCM_PORT"] = str(args.port)

    # Import mcp from main after setting env vars
    from ucm_mcp.main import mcp

    if args.http:
        # Run natively in the main thread (allows logs)
        uvicorn.run("ucm_mcp.main:app", host="127.0.0.1", port=args.port)
    else:
        # Run stdio in main thread, run UI http server in background
        t = threading.Thread(target=run_uvicorn, args=(args.port,), daemon=True)
        t.start()
        mcp.run()

if __name__ == "__main__":
    main()
