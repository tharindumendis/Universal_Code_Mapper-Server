import json
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter
from fastmcp import FastMCP
from ucm_mcp.tools.project_tools import resolve_project
from ucm_mcp.identity import get_db_id
from ucm_mcp.db.connection import get_connection
from ucm_mcp.web_socket_manager import send_tool_start_Message, send_tool_end_Message

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_search_tools(mcp: FastMCP, data_dir: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/search", tags=["search"])
    
    @router.post("/")
    @mcp.tool(description=
"""Search for symbols
Parameters:
'query' (exact/prefix) Optional
'keywords' (FTS5 search) Optional
'symbol_type' (default empty list)
'limit' (default 20)
'root_path' (Optional)"""
    )
    async def ucm_search(
        query: Optional[str] = None, 
        keywords: Optional[List[str]] = None, 
        symbol_type: Optional[str] = None, 
        limit: int = 20, 
        root_path: Optional[str] = None, 
        format_md: bool = True
    ) -> Union[str, List[Dict[str, Any]]]:
        tool_args = {"query": query, "keywords": keywords, "symbol_type": symbol_type, "limit": limit, "root_path": root_path, "format_md": format_md}
        await send_tool_start_Message("ucm_search", tool_args)
        if not query and not keywords:
            res = "Error: Must provide either 'query' or 'keywords' parameter." if format_md else []
            await send_tool_end_Message("ucm_search", tool_args, res)
            return res
            
        project_path = resolve_project(root_path)
        db_id = get_db_id(project_path)
        
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        if keywords:
            fts_query = " OR ".join(f'"{term}"*' for term in keywords)
            sql = """
                SELECT s.id, s.name, s.type, s.line, f.path
                FROM symbols_fts fts
                JOIN symbols s ON fts.rowid = s.id
                JOIN files f ON s.file_id = f.id
                WHERE symbols_fts MATCH ?
            """
            params = [fts_query]
            if symbol_type:
                sql += " AND s.type = ?"
                params.append(symbol_type)
            sql += " ORDER BY bm25(symbols_fts) LIMIT ?"
            params.append(limit)
        else:
            sql = """
                SELECT s.id, s.name, s.type, s.line, f.path
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE s.name LIKE ?
            """
            params = [f"%{query}%"]
            if symbol_type:
                sql += " AND s.type = ?"
                params.append(symbol_type)
            sql += " LIMIT ?"
            params.append(limit)
            
        cur.execute(sql, tuple(params))
        rows = [dict(row) for row in cur.fetchall()]
        
        if format_md:
            md = [f"## Search Results"]
            if not rows:
                md.append("- (No results found)")
            for r in rows:
                md.append(f"- **{r['type']}** `{r['name']}` ({r['path']}:{r['line']})")
            res = "\n".join(md)
            await send_tool_end_Message("ucm_search", tool_args, res)
            return res
            
        res = rows
        await send_tool_end_Message("ucm_search", tool_args, res)
        return res

    return router
