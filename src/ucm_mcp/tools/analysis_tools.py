from fastapi import APIRouter
from fastapi import FastAPI
import json
from typing import Optional, List, Dict, Any, Union
from fastmcp import FastMCP

from ucm_mcp.db.connection import get_connection
from ucm_mcp.identity import get_db_id
from ucm_mcp.tools.project_tools import resolve_project
from ucm_mcp.analysis.impact import calculate_impact
from ucm_mcp.analysis.dead_code import find_dead_code

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_analysis_tools(mcp: FastMCP, data_dir: str | None = None) -> None:
    
    router = APIRouter(prefix="/api/analysis", tags=["analysis"])

    @router.get("/impact-analysis")
    @mcp.tool(
        description="""Call when you need to find transitive callers/tests/routes affected by changing a symbol.
         Parameters: 
         'depth' controls analysis depth (default 3).
         'symbol_name' is the name of the symbol to analyze.
         'root_path' is the root path of the project."""
         )
    def ucm_impact_analysis(symbol_name: str, root_path: Optional[str] = None, depth: int = 3, format_md: bool = True) -> Union[str, List[str]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [str(e)]
            
        affected = calculate_impact(db_id, symbol_name, depth, data_dir)
        
        if format_md:
            if not affected:
                return f"No transitive callers found for '{symbol_name}'."
                
            lines = [f"## Impact Analysis for '{symbol_name}' (depth={depth}):"]
            for sym in affected:
                lines.append(f"- `{sym}`")
            return "\n".join(lines)
            
        return affected
        
    @router.post("/dead-code-detection")
    @mcp.tool(
        description="""Call when you need to find unreferenced symbols (functions/methods) indicating potential dead code.
         Parameters: 
         'symbol_types' [class, function] is a list of symbol types to filter by (default all).
         'root_path' is the root path of the project."""
         )
    def ucm_dead_code_detection(root_path: Optional[str] = None, symbol_types: Optional[List[str]] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [{"error": str(e)}]
            
        dead = find_dead_code(db_id, symbol_types, data_dir)
        
        if format_md:
            if not dead:
                return "No dead code found."
                
            lines = [f"## Potentially Unreferenced Symbols:"]
            for row in dead:
                lines.append(f"- {row['type']} `{row['name']}` ({row['path']}:{row['line']})")
            return "\n".join(lines)
            
        return dead

    @router.get("/duplicate-detection") 
    @mcp.tool(description="""Call when you need to find structurally similar or identically named function pairs.
    Parameters: 'root_path'  is the root path of the project."""
    )
    def ucm_duplicate_detection(root_path: Optional[str] = None, threshold: float = 0.85, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            return str(e) if format_md else [{"error": str(e)}]
            
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        cur.execute('''
            SELECT name, COUNT(*) as c
            FROM symbols
            WHERE type IN ('function', 'method')
            GROUP BY name
            HAVING c > 1
            ORDER BY c DESC
            LIMIT 20
        ''')
        
        rows = [dict(r) for r in cur.fetchall()]
        
        if format_md:
            if not rows:
                return "No duplicate named functions found."
                
            lines = ["## Functions with identical names across files (Naive similarity):"]
            for r in rows:
                lines.append(f"- `{r['name']}` (occurs {r['c']} times)")
            return "\n".join(lines)
            
        return rows
        
    return router
