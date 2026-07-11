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
from ucm_mcp.web_socket_manager import send_tool_start_Message, send_tool_end_Message

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_analysis_tools(mcp: FastMCP, data_dir: str | None = None) -> None:
    
    router = APIRouter(prefix="/api/analysis", tags=["analysis"])

    @router.get("/impact-analysis")
    @mcp.tool(
        description=
"""Find transitive callers/tests/routes affected by changing a symbol
Parameters: 
'depth' controls analysis depth (default 3)
'symbol_name' is the name of the symbol to analyze
'root_path' (Optional)"""
    )
    async def ucm_impact_analysis(symbol_name: str, root_path: Optional[str] = None, depth: int = 3, format_md: bool = True) -> Union[str, List[str]]:
        tool_args = {"symbol_name": symbol_name, "root_path": root_path, "depth": depth, "format_md": format_md}
        await send_tool_start_Message("ucm_impact_analysis", tool_args)
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            res = str(e) if format_md else [str(e)]
            await send_tool_end_Message("ucm_impact_analysis", tool_args, res)
            return res
            
        affected = calculate_impact(db_id, symbol_name, depth, data_dir)
        
        if format_md:
            if not affected:
                res = f"No transitive callers found for '{symbol_name}'."
                await send_tool_end_Message("ucm_impact_analysis", tool_args, res)
                return res
                
            lines = [f"## Impact Analysis for '{symbol_name}' (depth={depth}):"]
            for sym in affected:
                lines.append(f"- `{sym}`")
            res = "\n".join(lines)
            await send_tool_end_Message("ucm_impact_analysis", tool_args, res)
            return res
            
        res = affected
        await send_tool_end_Message("ucm_impact_analysis", tool_args, res)
        return res
        
    @router.post("/dead-code-detection")
    @mcp.tool(
        description=
"""Find unreferenced symbols indicating potential dead code
Parameters: 
'symbol_types' [function, class, ...] (default all).
'root_path' (Optional)"""
         )
    async def ucm_dead_code_detection(root_path: Optional[str] = None, symbol_types: Optional[List[str]] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        tool_args = {"root_path": root_path, "symbol_types": symbol_types, "format_md": format_md}
        await send_tool_start_Message("ucm_dead_code_detection", tool_args)
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            res = str(e) if format_md else [{"error": str(e)}]
            await send_tool_end_Message("ucm_dead_code_detection", tool_args, res)
            return res
            
        dead = find_dead_code(db_id, symbol_types, data_dir)
        
        if format_md:
            if not dead:
                res = "No dead code found."
                await send_tool_end_Message("ucm_dead_code_detection", tool_args, res)
                return res
                
            lines = [f"## Potentially Unreferenced Symbols:"]
            for row in dead:
                lines.append(f"- {row['type']} `{row['name']}` ({row['path']}:{row['line']})")
            res = "\n".join(lines)
            await send_tool_end_Message("ucm_dead_code_detection", tool_args, res)
            return res
            
        res = dead
        await send_tool_end_Message("ucm_dead_code_detection", tool_args, res)
        return res

    @router.get("/duplicate-detection") 
    @mcp.tool(description=
"""Find structurally similar or identically named function pairs
Parameters:
'root_path' (Optional)"""
    )
    async def ucm_duplicate_detection(root_path: Optional[str] = None, threshold: float = 0.85, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        tool_args = {"root_path": root_path, "threshold": threshold, "format_md": format_md}
        await send_tool_start_Message("ucm_duplicate_detection", tool_args)
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            res = str(e) if format_md else [{"error": str(e)}]
            await send_tool_end_Message("ucm_duplicate_detection", tool_args, res)
            return res
            
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
                res = "No duplicate named functions found."
                await send_tool_end_Message("ucm_duplicate_detection", tool_args, res)
                return res
                
            lines = ["## Functions with identical names across files (Naive similarity):"]
            for r in rows:
                lines.append(f"- `{r['name']}` (occurs {r['c']} times)")
            res = "\n".join(lines)
            await send_tool_end_Message("ucm_duplicate_detection", tool_args, res)
            return res
            
        res = rows
        await send_tool_end_Message("ucm_duplicate_detection", tool_args, res)
        return res
        
    return router
