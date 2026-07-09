import os
import json
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from ucm_mcp.db.connection import get_connection
from ucm_mcp.identity import get_db_id
from ucm_mcp.tools.project_tools import resolve_project


def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_graph_tools(mcp: FastMCP, data_dir: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/graph", tags=["graph"])
    
    @router.get("/calls")
    @mcp.tool(description=
"""Find functions/methods that call or are called by a symbol
Parameters:
'direction' (callers, callees), (default both)
'symbol_name'
'root_path' (Optional)"""
    )
    async def ucm_find_calls(symbol_name: str, direction: str = "both", root_path: Optional[str] = None, format_md: bool = True) -> Union[str, Dict[str, Any]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else {"error": str(e)}
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        res = {}
        
        if direction in ("callers", "both"):
            cur.execute('''
                SELECT c.line, s.name as caller_name, s.type as caller_type, f.path
                FROM calls c
                JOIN symbols s ON c.caller_symbol_id = s.id
                JOIN files f ON s.file_id = f.id
                WHERE c.callee_name = ?
            ''', (symbol_name,))
            res["callers"] = [dict(r) for r in cur.fetchall()]
            
        if direction in ("callees", "both"):
            cur.execute('''
                SELECT c.callee_name, c.line, f.path
                FROM calls c
                JOIN symbols s ON c.caller_symbol_id = s.id
                JOIN files f ON s.file_id = f.id
                WHERE s.name = ?
            ''', (symbol_name,))
            res["callees"] = [dict(r) for r in cur.fetchall()]
            
        if format_md:
            lines = [f"## Calls for '{symbol_name}'"]
            if "callers" in res:
                lines.append("### Callers (who calls this):")
                if not res["callers"]:
                    lines.append("- (None found)")
                for r in res["callers"]:
                    lines.append(f"- {r['caller_type']} `{r['caller_name']}` ({r['path']}:{r['line']})")
            if "callees" in res:
                lines.append("### Callees (who this calls):")
                if not res["callees"]:
                    lines.append("- (None found)")
                for r in res["callees"]:
                    lines.append(f"- `{r['callee_name']}` ({r['path']}:{r['line']})")
            return "\n".join(lines)
            
        return res
        
    @router.get("/dependencies")
    @mcp.tool(description=
"""Find what modules or files a specific file imports
Parameters:
'file_path'
'root_path' (Optional)"""
    )
    def ucm_dependencies(file_path: str, root_path: Optional[str] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [{"error": str(e)}]
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        path_norm = _normalize_path(file_path)
        
        cur.execute('''
            SELECT i.to_module, i.alias, i.is_dynamic
            FROM imports i
            JOIN files f ON i.from_file_id = f.id
            WHERE f.path LIKE ? OR f.path = ?
        ''', (f"%{path_norm}%", path_norm))
        
        rows = [dict(r) for r in cur.fetchall()]
        
        if format_md:
            if not rows:
                return f"No imports found for '{file_path}'."
            lines = [f"## Dependencies of '{file_path}':"]
            for r in rows:
                alias = f" as {r['alias']}" if r["alias"] else ""
                dyn = " (dynamic)" if r["is_dynamic"] else ""
                lines.append(f"- `{r['to_module']}`{alias}{dyn}")
            return "\n".join(lines)
            
        return rows
        
    @router.get("/inheritance")
    @mcp.tool(description=
"""Find parent/child inheritance relationships for a class
Parameters:
'symbol_name'
'root_path' (Optional)"""
    )
    def ucm_inheritance(symbol_name: str, root_path: Optional[str] = None, format_md: bool = True) -> Union[str, Dict[str, Any]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else {"error": str(e)}
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        cur.execute('''
            SELECT i.parent_name, i.kind, f.path
            FROM inheritance i
            JOIN symbols s ON i.child_symbol_id = s.id
            JOIN files f ON s.file_id = f.id
            WHERE s.name = ?
        ''', (symbol_name,))
        parents = [dict(r) for r in cur.fetchall()]
        
        cur.execute('''
            SELECT s.name as child_name, i.kind, f.path
            FROM inheritance i
            JOIN symbols s ON i.child_symbol_id = s.id
            JOIN files f ON s.file_id = f.id
            WHERE i.parent_name = ?
        ''', (symbol_name,))
        children = [dict(r) for r in cur.fetchall()]
        
        res = {"parents": parents, "children": children}
        
        if format_md:
            if not parents and not children:
                return f"No inheritance relationships found for '{symbol_name}'."
            lines = [f"## Inheritance for '{symbol_name}':"]
            if parents:
                lines.append("### Parents:")
                for p in parents:
                    lines.append(f"- {p['kind']} `{p['parent_name']}` ({p['path']})")
            if children:
                lines.append("### Children:")
                for c in children:
                    lines.append(f"- `{c['child_name']}` {c['kind']} this ({c['path']})")
            return "\n".join(lines)
            
        return res

    @router.get("/dependents")
    @mcp.tool(description=
"""Find what modules or files import a specific file
Parameters:
'file_path'
'root_path' (Optional)"""
    )
    def ucm_dependents(file_path: str, root_path: Optional[str] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [{"error": str(e)}]
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        file_path = _normalize_path(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        cur.execute('''
            SELECT f.path, i.is_dynamic, i.alias
            FROM imports i
            JOIN files f ON i.from_file_id = f.id
            WHERE i.to_module LIKE ? OR i.to_module = ?
        ''', (f"%{base_name}%", base_name))
        
        rows = [dict(r) for r in cur.fetchall()]
        
        if format_md:
            if not rows:
                return f"No dependents found for '{file_path}' (no files seem to import it)."
            lines = [f"## Dependents of '{file_path}':"]
            for r in rows:
                dyn = " (dynamic)" if r["is_dynamic"] else ""
                lines.append(f"- `{r['path']}`{dyn}")
            return "\n".join(lines)
            
        return rows

    return router
