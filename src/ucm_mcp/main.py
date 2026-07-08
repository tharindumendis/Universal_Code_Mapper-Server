from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Any, Dict
import asyncio

from ucm_mcp.server import build_server

newMCP = FastMCP("ucm_mcp")
mcp_app = newMCP.http_app(path="/")
app = FastAPI(title="UCM API", lifespan=mcp_app.lifespan)
mcp, app = build_server(mcp=newMCP, app=app)

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

# Mount the MCP SSE application on a subpath to prevent it from overriding the / routes.
app.mount("/mcp", mcp_app)
