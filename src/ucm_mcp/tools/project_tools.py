from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastmcp import FastMCP
from ucm_mcp.indexing.indexer import index_project_impl
from ucm_mcp.identity import list_projects, canonicalize_path
from ucm_mcp.cli import FRONTEND_URL
from ucm_mcp.web_socket_manager import send_tool_start_Message, send_tool_end_Message

_ACTIVE_PROJECT: Optional[str] = None

def resolve_project(root_path: Optional[str]) -> str:
    if root_path is not None:
        return canonicalize_path(root_path)
    if _ACTIVE_PROJECT is not None:
        return _ACTIVE_PROJECT
    raise ValueError("No active project set. Call ucm_set_active_project or pass root_path.")

def register_project_tools(mcp: FastMCP, data_dir: str | None = None, port: int = 51000) -> APIRouter:
    router = APIRouter(prefix="/api/project", tags=["project"])
    
    @router.post("/index")
    @mcp.tool(description=
"""Index a project for the first time or re-index it
Parameters:
'root_path'
'force_full' (Default False)
'watch' (Default True)"""
    )
    async def ucm_index_project(root_path: str, force_full: bool = False, watch: bool = True) -> str:
        tool_args = {"root_path": root_path, "force_full": force_full, "watch": watch}
        await send_tool_start_Message("ucm_index_project", tool_args)
        db_id = index_project_impl(root_path, data_dir=data_dir, force_full=force_full, watch=watch)
        res = f"Project indexed successfully. db_id: {db_id}"
        await send_tool_end_Message("ucm_index_project", tool_args, res)
        return res

    @router.post("/active")
    @mcp.tool(description=
"""Set the active project context for subsequent queries.
Parameters:
'root_path' (string) path to the project.
""")
    async def ucm_set_active_project(root_path: str) -> str:
        tool_args = {"root_path": root_path}
        await send_tool_start_Message("ucm_set_active_project", tool_args)
        global _ACTIVE_PROJECT
        _ACTIVE_PROJECT = canonicalize_path(root_path)
        res = f"Active project set to {_ACTIVE_PROJECT}"
        await send_tool_end_Message("ucm_set_active_project", tool_args, res)
        return res

    @router.get("/list")
    @mcp.tool(description=f"""See all currently indexed projects
Parameters:
'root_path'

# UCM Tool Tips

### UCM UI

Send this URL to user to see UCM UI: {FRONTEND_URL}/?port={port}

### Common Flow

1. Index project using 'ucm_index_project' (with --force_full for full re-index if needed,) once index it will watch the file changes and update the index automatically.
2. Active Project Once using 'ucm_set_active_project', then you don't need to provide the root_path in the subsequent tool calls.
3. Use UCM tools without passing 'root_path', it will use the active project.

## UCM Tools Parameter Description

1. 'root_path' (string) path to the project.
2. 'symbol_types' (function, class, method, variable, interface).
3. 'symbol_name' name of the symbol. (ex. get_data, process).
4. 'file_path' path to the file from root_path (ex. "[root_dir]/src/data/x.py).""")
    async def ucm_list_projects() -> List[Dict[str, Any]]:
        tool_args = {}
        await send_tool_start_Message("ucm_list_projects", tool_args)
        projects = list_projects(data_dir=data_dir)
        res = [dict(p) for p in projects]
        await send_tool_end_Message("ucm_list_projects", tool_args, res)
        return res

    return router
