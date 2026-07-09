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

newMCP = FastMCP("ucm_mcp")
mcp_app = newMCP.http_app(path="/")

@contextlib.asynccontextmanager
async def app_lifespan(app: FastAPI):
    port = os.environ.get("UCM_PORT", "8000")
    print("\n" + "="*60, file=sys.stderr)
    print("🚀 UCM Backend is running!", file=sys.stderr)
    print(f"🌐 Open the UI at: https://ucm-ui.netlify.app/?port={port}", file=sys.stderr)
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

@app.get("/view", response_class=HTMLResponse)
def view_graph():
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>UCM Directory Map Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; background-color: #fafafa; }
        #header { padding: 15px; background: #ffffff; border-bottom: 1px solid #e0e0e0; display: flex; gap: 15px; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        #header input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; width: 300px; }
        #header button { padding: 8px 16px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold; }
        #header button:hover { background-color: #0056b3; }
        #status { font-size: 14px; color: #666; }
        #mynetwork { flex-grow: 1; border: none; outline: none; }
    </style>
</head>
<body>
    <div id="header">
        <input type="text" id="rootPath" placeholder="Project Root Path (e.g. d:\\DEV\\mcp\\Code-Mapper)" />
        <button onclick="loadGraph()">Load Directory Map</button>
        <span id="status"></span>
    </div>
    <div id="mynetwork"></div>

    <script type="text/javascript">
        let network = null;

        async function loadGraph() {
            const rootPath = document.getElementById('rootPath').value;
            if (!rootPath) return alert("Please enter a Project Root Path");

            document.getElementById('status').innerText = "Loading...";

            let url = `/overview/directory-map?format_md=false&root_path=${encodeURIComponent(rootPath)}&include_symbols=true`;

            try {
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }

                drawGraph(data);
                document.getElementById('status').innerText = "Done";
            } catch (err) {
                document.getElementById('status').innerText = "Error: " + err.message;
            }
        }

        function drawGraph(data) {
            const nodes = new vis.DataSet();
            const edges = new vis.DataSet();
            
            let nodeIdCounter = 0;
            
            // Add central root node
            const rootId = `node_${nodeIdCounter++}`;
            nodes.add({ id: rootId, label: (data.directory || 'Project'), color: '#ffcc00', shape: 'box', font: { face: 'monospace' } });

            function traverse(nodeList, parentId) {
                if (!nodeList) return;
                nodeList.forEach(item => {
                    const id = `node_${nodeIdCounter++}`;
                    
                    let shape = 'text';
                    let color = '#ffffff';
                    let label = item.name;
                    let title = item.name;
                    
                    if (item.type === 'dir') {
                        shape = 'box';
                        color = '#ffcc00'; // folder color
                    } else if (item.type === 'file') {
                        shape = 'text';
                        color = '#ffffff'; // file color
                    } else {
                        shape = 'text';
                        color = '#ccffcc'; // symbol color
                        if (item.line !== undefined) {
                            title += " (Line " + item.line + ")";
                        }
                    }
                    
                    nodes.add({ id: id, label: label, title: title, shape: shape, color: color, font: { face: 'monospace' } });
                    edges.add({ from: parentId, to: id, color: '#ccc' });
                    
                    if (item.children && item.children.length > 0) {
                        traverse(item.children, id);
                    }
                });
            }

            traverse(data.tree, rootId);

            const container = document.getElementById('mynetwork');
            const graphData = { nodes: nodes, edges: edges };
            const options = {
                physics: {
                    barnesHut: {
                        gravitationalConstant: -2000,
                        centralGravity: 0.3,
                        springLength: 95
                    }
                }
            };
            if (network) network.destroy();
            network = new vis.Network(container, graphData, options);
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

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
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
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
        # Call the tool through FastMCP
        result = await mcp.call_tool(tool_name, payload)
        
        # Result is likely a CallToolResult pydantic model or list of contents
        if hasattr(result, "model_dump"):
            return {"result": result.model_dump()}
        elif hasattr(result, "dict"):
            return {"result": result.dict()}
        elif isinstance(result, list):
            formatted = []
            for item in result:
                if hasattr(item, "model_dump"):
                    formatted.append(item.model_dump())
                elif hasattr(item, "dict"):
                    formatted.append(item.dict())
                else:
                    formatted.append(str(item))
            return {"result": formatted}
        
        return {"result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/index")
async def websocket_index(websocket: WebSocket):
    await websocket.accept()
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
                        asyncio.run_coroutine_threadsafe(websocket.send_json({"status": "error", "message": str(e)}), loop)
                t = threading.Thread(target=run_indexer)
                t.start()
    except WebSocketDisconnect:
        pass

# Mount the MCP SSE application on a subpath to prevent it from overriding the / routes.
app.mount("/mcp", mcp_app)
