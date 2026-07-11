from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Any, Dict
import asyncio
import threading

import contextlib
import os
import sys

from fastapi.middleware.cors import CORSMiddleware
from ucm_mcp.server import build_server
from ucm_mcp.logger import get_logger
from ucm_mcp.cli import FRONTEND_URL
from ucm_mcp.web_socket_manager import web_socket_manager, ToolStartMessage, ToolEndMessage, ToolName
import time

logger = get_logger(__name__)

newMCP = FastMCP("ucm_mcp")
mcp_app = newMCP.http_app(path="/")
@contextlib.asynccontextmanager
async def app_lifespan(app: FastAPI):
    port = os.environ.get("UCM_PORT", "510000")
    print("\n" + "="*60, file=sys.stderr)
    print("🚀 UCM Backend is running!", file=sys.stderr)
    print(f"🌐 Open the UI at: {FRONTEND_URL}/?port={port}", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)
    async with mcp_app.lifespan(app) as ctx:
        yield ctx

app = FastAPI(title="UCM API", lifespan=app_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_dir = os.environ.get("UCM_DATA_DIR")
mcp, app = build_server(data_dir=data_dir, mcp=newMCP, app=app)

# We will create the mcp_app but mount it under a specific path so it doesn't shadow everything


@app.get("/")
def read_root():
    return {"health": "ok", "message": "UCM API Server is running."}

@app.get("/api/graph")
async def export_graph(root_path: str):
    """Export the full graph including files, symbols, routes, and relationships."""
    from ucm_mcp.tools.project_tools import resolve_project
    from ucm_mcp.identity import get_db_id
    from ucm_mcp.analysis.export import get_full_graph
    
    try:
        project_path = resolve_project(root_path)
        db_id = get_db_id(project_path)
        # Assuming data_dir handling is default for now
        graph_data = get_full_graph(db_id, data_dir=None)
        return graph_data
    except ValueError as e:
        if str(e) == "Project not indexed":
            raise HTTPException(status_code=404, detail=str(e))
        logger.exception("Error exporting graph")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error exporting graph")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def list_tools():
    """List all available tools in the MCP server."""
    # Internal tools list is typically accessible via _list_tools() or mcp.tools
    tools = await mcp._list_tools() if asyncio.iscoroutinefunction(getattr(mcp, '_list_tools', None)) else mcp._list_tools()
    
    tools_list = []
    for tool in tools:
        # tool is likely a FunctionTool object
        tools_list.append({
            "name": getattr(tool, "name", str(tool)),
            "description": getattr(tool, "description", ""),
        })
    return {"tools": tools_list}

@app.post("/api/tools/{tool_name}")
async def call_tool_api(tool_name: str, payload: Dict[str, Any] = None):
    """Call a specific tool by name with the given JSON payload."""
    if payload is None:
        payload = {}
        
    try:
        start_msg = ToolStartMessage(
            content=f"Starting tool {tool_name}",
            timestamp=int(time.time() * 1000),
            toolName=tool_name,
            toolArgs=payload
        )
        await web_socket_manager.broadcast(start_msg)
    except Exception as e:
        logger.warning(f"Could not broadcast tool start: {e}")

    try:
        # Call the tool through FastMCP
        print(f" this is from tool call endpoint {tool_name} {payload} ")
        result = await mcp.call_tool(tool_name, payload)
        
        # Result is likely a CallToolResult pydantic model or list of contents
        formatted_result = None
        if hasattr(result, "model_dump"):
            formatted_result = result.model_dump()
        elif hasattr(result, "dict"):
            formatted_result = result.dict()
        elif isinstance(result, list):
            formatted = []
            for item in result:
                if hasattr(item, "model_dump"):
                    formatted.append(item.model_dump())
                elif hasattr(item, "dict"):
                    formatted.append(item.dict())
                else:
                    formatted.append(str(item))
            formatted_result = formatted
        else:
            formatted_result = str(result)
            
        try:
            end_msg = ToolEndMessage(
                content=f"Finished tool {tool_name}",
                timestamp=int(time.time() * 1000),
                toolName=tool_name,
                toolArgs=payload,
                toolResult={"result": formatted_result} if not isinstance(formatted_result, dict) else formatted_result
            )
            await web_socket_manager.broadcast(end_msg)
        except Exception as e:
            logger.warning(f"Could not broadcast tool end: {e}")
            
        return {"result": formatted_result}
    except Exception as e:
        logger.exception(f"Error calling tool {tool_name}")
        try:
            err_msg = ToolEndMessage(
                content=f"Error running tool {tool_name}: {str(e)}",
                timestamp=int(time.time() * 1000),
                toolName=tool_name,
                toolArgs=payload,
                toolResult={"error": str(e)}
            )
            err_msg.isError = True
            await web_socket_manager.broadcast(err_msg)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/index")
async def websocket_index(websocket: WebSocket):
    # await websocket.accept()
    await web_socket_manager.connect(websocket)
    loop = asyncio.get_running_loop()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "index":
                root_path = data.get("root_path")
                force_full = data.get("force_full", False)
                def run_indexer():
                    try:
                        asyncio.run_coroutine_threadsafe(websocket.send_json({"status": "indexing", "message": f"Indexing {root_path}..."}), loop)
                        from ucm_mcp.indexing.indexer import index_project_impl
                        db_id = index_project_impl(root_path, data_dir=None, force_full=force_full, watch=True)
                        asyncio.run_coroutine_threadsafe(websocket.send_json({"status": "complete", "db_id": db_id}), loop)
                    except Exception as e:
                        logger.exception("Error in websocket indexing thread")
                        asyncio.run_coroutine_threadsafe(websocket.send_json({"status": "error", "message": str(e)}), loop)
                t = threading.Thread(target=run_indexer)
                t.start()
    except WebSocketDisconnect:
        await web_socket_manager.disconnect(websocket)
        pass

# Mount the MCP SSE application on a subpath to prevent it from overriding the / routes.
app.mount("/mcp", mcp_app)
