from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastmcp import FastMCP
from ucm_mcp.indexing.indexer import index_project_impl
from ucm_mcp.identity import list_projects, canonicalize_path
from ucm_mcp.cli import FRONTEND_URL

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
    def ucm_index_project(root_path: str, force_full: bool = False, watch: bool = True) -> str:
        db_id = index_project_impl(root_path, data_dir=data_dir, force_full=force_full, watch=watch)
        return f"Project indexed successfully. db_id: {db_id}"

    @router.post("/active")
    @mcp.tool(description=
"""Set the active project context for subsequent queries.
Parameters:
'root_path' (string) path to the project.
""")
    def ucm_set_active_project(root_path: str) -> str:
        global _ACTIVE_PROJECT
        _ACTIVE_PROJECT = canonicalize_path(root_path)
        return f"Active project set to {_ACTIVE_PROJECT}"

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
    def ucm_list_projects() -> List[Dict[str, Any]]:
        projects = list_projects(data_dir=data_dir)
        return [dict(p) for p in projects]

    return router
