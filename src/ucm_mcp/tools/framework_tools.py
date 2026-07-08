import json
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter
from fastmcp import FastMCP

from ucm_mcp.db.connection import get_connection
from ucm_mcp.identity import get_db_id
from ucm_mcp.tools.project_tools import resolve_project

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_framework_tools(mcp: FastMCP, data_dir: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/framework", tags=["framework"])
    
    @router.get("/routes")
    @mcp.tool(description="""Call when you need to find the controller/handler for a given API route. Applicable ONLY to web frameworks (e.g. Flask, Django, React, Express, etc.).
    Do NOT use for CLI or non-web applications.
    Parameters:
    'root_path' (Optional[str]): The root path of the project.
    'method' (Optional[str]): The HTTP method of the route (e.g., 'GET').
    'path' (Optional[str]): The path of the route (e.g., '/api/users')."""
    )
    def ucm_route_lookup(root_path: Optional[str] = None, method: Optional[str] = None, path: Optional[str] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [{"error": str(e)}]
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        sql = '''SELECT r.method, r.path, s.name as handler_name, f.path as file_path, r.framework
            FROM routes r
            LEFT JOIN symbols s ON r.handler_symbol_id = s.id
            LEFT JOIN files f ON r.file_id = f.id
            WHERE 1=1
        '''
        params = []
        if method:
            sql += " AND r.method = ?"
            params.append(method.upper())
        if path:
            sql += " AND r.path LIKE ?"
            params.append(f"%{path}%")
            
        cur.execute(sql, tuple(params))
        rows = [dict(r) for r in cur.fetchall()]
        
        if format_md:
            if not rows:
                return "No routes found matching the criteria."
                
            lines = ["## Routes found:"]
            for r in rows:
                handler = r['handler_name'] or "UnknownHandler"
                file_p = r['file_path'] or "UnknownFile"
                lines.append(f"- `[{r['framework']}]` {r['method']} `{r['path']}` -> {handler} ({file_p})")
            return "\n".join(lines)
            
        return rows
        
    @router.get("/architecture")
    @mcp.tool(description="""Call when you need a breakdown of the project architecture (Controllers, Services, Models, etc.) based on file and symbol conventions.
    Parameters:
    'root_path' (Optional[str]): The root path of the project."""
    )
    def ucm_architecture_summary(root_path: Optional[str] = None, format_md: bool = True) -> Union[str, Dict[str, Any]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else {"error": str(e)}
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        # Extremely basic heuristic breakdown
        cur.execute("SELECT path FROM files")
        files = cur.fetchall()
        
        controllers = 0
        services = 0
        models = 0
        tests = 0
        utils = 0
        
        for r in files:
            p = r["path"].lower()
            if "test" in p:
                tests += 1
            elif "view" in p or "controller" in p or "route" in p:
                controllers += 1
            elif "service" in p:
                services += 1
            elif "model" in p or "entity" in p or "schema" in p:
                models += 1
            elif "util" in p or "helper" in p:
                utils += 1
                
        res = {
            "controllers": controllers,
            "services": services,
            "models": models,
            "utilities": utils,
            "tests": tests
        }
        
        if format_md:
            return (
                "## Architecture Breakdown (Heuristic):\n"
                f"- **Controllers/Views**: {controllers} files\n"
                f"- **Services/Business Logic**: {services} files\n"
                f"- **Models/Entities**: {models} files\n"
                f"- **Utilities/Helpers**: {utils} files\n"
                f"- **Tests**: {tests} files"
            )
            
        return res

    return router
