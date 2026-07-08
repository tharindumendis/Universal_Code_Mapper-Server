from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastmcp import FastMCP
from ucm_mcp.indexing.indexer import index_project_impl
from ucm_mcp.identity import list_projects, canonicalize_path

_ACTIVE_PROJECT: Optional[str] = None

def resolve_project(root_path: Optional[str]) -> str:
    if root_path is not None:
        return canonicalize_path(root_path)
    if _ACTIVE_PROJECT is not None:
        return _ACTIVE_PROJECT
    raise ValueError("No active project set. Call ucm_set_active_project or pass root_path.")

def register_project_tools(mcp: FastMCP, data_dir: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/project", tags=["project"])
    
    @router.post("/index")
    @mcp.tool(description="""Call when you need to index a project for the first time or re-index it.
    Parameters: 
    'root_path' (string) path to the project.
    'force_full' (bool) for full re-index."""
    )
    def ucm_index_project(root_path: str, force_full: bool = False, watch: bool = True) -> str:
        db_id = index_project_impl(root_path, data_dir=data_dir, force_full=force_full, watch=watch)
        return f"Project indexed successfully. db_id: {db_id}"

    @router.post("/active")
    @mcp.tool(description="Call when you need to set the active project context for subsequent queries.")
    def ucm_set_active_project(root_path: str) -> str:
        global _ACTIVE_PROJECT
        _ACTIVE_PROJECT = canonicalize_path(root_path)
        return f"Active project set to {_ACTIVE_PROJECT}"

    @router.get("/list")
    @mcp.tool(description="""Call when you need to see all currently indexed projects.
    Parameters:
    'root_path' (string) path to the project.
    Tips:
    if you active current project using this tool you can ignore root_path parameter of other umc tools.
    in umc tool set
    'symbol' means class, function, method, interface, struct, etc.
    """)
    def ucm_list_projects() -> List[Dict[str, Any]]:
        projects = list_projects(data_dir=data_dir)
        return [dict(p) for p in projects]

    return router
