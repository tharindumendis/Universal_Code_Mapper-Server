import json
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter
from fastmcp import FastMCP

from ucm_mcp.db.connection import get_connection
from ucm_mcp.identity import get_db_id
from ucm_mcp.tools.project_tools import resolve_project

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_test_tools(mcp: FastMCP, data_dir: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/test", tags=["test"])
    
    @router.get("/lookup")
    @mcp.tool(description=
"""Tests that likely cover or reference a given symbol
Parameters:
'symbol_name'
'root_path' (Optional)"""
    )
    def ucm_test_lookup(symbol_name: str, root_path: Optional[str] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [{"error": str(e)}]
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        # Heuristic: search for functions/methods whose name contains 'test' AND 
        # either their name contains the symbol name or they are in a test file
        # containing calls to the symbol.
        
        cur.execute('''
            SELECT s.name, f.path, s.line
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE s.name LIKE ? AND s.name LIKE '%test%'
        ''', (f"%{symbol_name}%",))
        
        rows = cur.fetchall()
        
        # Also let's find calls from test files to this symbol
        cur.execute('''
            SELECT c.line, s.name as caller_name, f.path
            FROM calls c
            JOIN symbols s ON c.caller_symbol_id = s.id
            JOIN files f ON s.file_id = f.id
            WHERE c.callee_name = ? AND f.path LIKE '%test%'
        ''', (symbol_name,))
        
        calls = cur.fetchall()
        
        results = []
        for r in rows:
            results.append({"name": r["name"], "path": r["path"], "line": r["line"], "type": "test_symbol"})
        for c in calls:
            results.append({"name": c["caller_name"], "path": c["path"], "line": c["line"], "type": "call_from_test"})
        
        if format_md:
            if not rows and not calls:
                return f"No tests found covering '{symbol_name}'."
                
            lines = [f"## Tests covering '{symbol_name}':"]
            seen = set()
            for r in rows:
                desc = f"- `{r['name']}` ({r['path']}:{r['line']})"
                if desc not in seen:
                    seen.add(desc)
                    lines.append(desc)
                    
            for c in calls:
                desc = f"- `{c['caller_name']}` ({c['path']}:{c['line']})"
                if desc not in seen:
                    seen.add(desc)
                    lines.append(desc)
                    
            return "\n".join(lines)
            
        return results

    return router
