from ucm_mcp.web_socket_manager import WebSocketMessage
import json
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter
from fastmcp import FastMCP
from ucm_mcp.tools.project_tools import resolve_project
from ucm_mcp.identity import get_db_id
from pydantic import BaseModel
from ucm_mcp.db.repository import get_file_counts, get_total_file_count
from ucm_mcp.db.connection import get_connection
from ucm_mcp.logger import get_logger
from ucm_mcp.web_socket_manager import web_socket_manager, send_tool_start_Message, send_tool_end_Message

logger = get_logger(__name__)

class SymbolNode(BaseModel):
    name: str
    type: str
    line: int

class FileNode(BaseModel):
    name: str
    type: str = "file"
    children: List[SymbolNode] = []

class DirNode(BaseModel):
    name: str
    type: str = "dir"
    children: List[Union['DirNode', FileNode]] = []

class DirectoryMapResponse(BaseModel):
    directory: str
    tree: List[Union[DirNode, FileNode]]

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_overview_tools(mcp: FastMCP, data_dir: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/overview", tags=["overview"])
    
    @router.get("/project")
    @mcp.tool(description=
"""High-level overview of the project, including file counts and language breakdown
Parameters:
'root_path' (Optional)"""
    )
    async def ucm_project_overview(root_path: Optional[str] = None, format_md: bool = True) -> Union[str, Dict[str, Any]]:
        tool_args = {"root_path": root_path, "format_md": format_md}
        await send_tool_start_Message("ucm_project_overview", tool_args)

        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            res = str(e) if format_md else {"error": str(e)}
            await send_tool_end_Message("ucm_project_overview", tool_args, res)
            return res
        
        counts = get_file_counts(db_id, data_dir=data_dir)
        total = get_total_file_count(db_id, data_dir=data_dir)
        
        res = {
            "project_path": project_path,
            "total_files": total,
            "language_breakdown": counts
        }
        
        if format_md:
            md = [f"# Project Overview: {project_path}", f"- **Total Files**: {total}", "- **Language Breakdown**:"]
            for lang, count in counts.items():
                md.append(f"  - {lang or 'Unknown'}: {count}")
            await send_tool_end_Message("ucm_project_overview", {"root_path": root_path, "format_md": format_md}, res)
            return "\n".join(md)
        await send_tool_end_Message("ucm_project_overview", {"root_path": root_path, "format_md": format_md}, res)
        return res

    @router.get("/directory-map")
    @mcp.tool(description=
"""List files, subdirectories and symbols within a specific directory
Parameters:
'dir_path' (optional, root if omitted).
'root_path' (Optional).
'depth' (default 1).
'include_symbols' whether to include symbols as children of files (default True)"""
    )
    async def ucm_directory_map(dir_path: Optional[str] = None, root_path: Optional[str] = None, depth: int = 1, include_symbols: bool = True, format_md: bool = True) -> Union[str, Dict[str, Any], DirectoryMapResponse]:
        tool_args = {"dir_path": dir_path, "root_path": root_path, "depth": depth, "include_symbols": include_symbols, "format_md": format_md}
        await send_tool_start_Message("ucm_directory_map", tool_args)
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            res = str(e) if format_md else {"error": str(e)}
            await send_tool_end_Message("ucm_directory_map", tool_args, res)
            return res
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        dir_path = _normalize_path(dir_path) if dir_path else ""
        if dir_path and not dir_path.endswith('/'):
            dir_path += '/'
        
        if dir_path:
            cur.execute("SELECT path FROM files WHERE path LIKE ?", (f"{dir_path}%",))
        else:
            cur.execute("SELECT path FROM files")
            
        files = [{"path": r["path"]} for r in cur.fetchall()]
        
        file_symbols = {}
        if include_symbols:
            if dir_path:
                cur.execute("""
                    SELECT s.name, s.type, s.line, f.path
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    WHERE f.path LIKE ?
                """, (f"{dir_path}%",))
            else:
                cur.execute("""
                    SELECT s.name, s.type, s.line, f.path
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                """)
            for r in cur.fetchall():
                path = r["path"]
                if path not in file_symbols:
                    file_symbols[path] = []
                file_symbols[path].append({
                    "name": r["name"],
                    "type": r["type"],
                    "line": r["line"]
                })
        
        paths = sorted([f["path"] for f in files])
        
        # Group into a tree structure
        tree_dict = {}
        for p in paths:
            rel = p[len(dir_path):].lstrip('/')
            if not rel:
                continue
            parts = rel.split('/')
            curr = tree_dict
            for i, part in enumerate(parts):
                is_file = (i == len(parts) - 1)
                if is_file:
                    curr[part] = file_symbols.get(p, []) if include_symbols else "file"
                else:
                    if part not in curr or not isinstance(curr[part], dict):
                        curr[part] = {"type": "dir", "children": {}}
                    curr = curr[part]["children"]
                    
        def _convert_to_nodes(d) -> List[Union['DirNode', FileNode]]:
            res = []
            for k in sorted(d.keys()):
                v = d[k]
                if isinstance(v, list) or v == "file":
                    symbols = v if isinstance(v, list) else []
                    sym_nodes = [SymbolNode(name=s["name"], type=s["type"], line=s["line"]) for s in symbols]
                    res.append(FileNode(name=k, children=sym_nodes))
                else:
                    res.append(DirNode(name=k, children=_convert_to_nodes(v["children"])))
            return res
            
        tree_nodes = _convert_to_nodes(tree_dict)
        
        if format_md:
            display_path = dir_path.rstrip('/') or project_path
            md = [f"## Directory Map: {display_path}"]
            
            if not files:
                import os
                full_path = os.path.join(project_path, dir_path)
                if not os.path.exists(full_path):
                    md.append(f"- (Error: Directory '{display_path}' does not exist)")
                else:
                    md.append(f"- (Error: Directory '{display_path}' is empty or contains no indexed files)")
                res = "\n".join(md)
                await send_tool_end_Message("ucm_directory_map", {"dir_path": dir_path, "root_path": root_path, "depth": depth, "include_symbols": include_symbols, "format_md": format_md}, res)
                return res
            
            def _print_tree(node_list: List[Union['DirNode', FileNode]], indent_level=0):
                lines = []
                indent = "  " * indent_level
                for node in node_list:
                    if isinstance(node, FileNode):
                        lines.append(f"{indent}- {node.name}")
                        for child in node.children:
                            lines.append(f"{indent}  - [{child.type}] {child.name} (Line {child.line})")
                    elif isinstance(node, DirNode):
                        lines.append(f"{indent}- {node.name}/")
                        lines.extend(_print_tree(node.children, indent_level + 1))
                return lines
                
            md.extend(_print_tree(tree_nodes))
            res = "\n".join(md)
            await send_tool_end_Message("ucm_directory_map", {"dir_path": dir_path, "root_path": root_path, "depth": depth, "include_symbols": include_symbols, "format_md": format_md}, res)
            return res
        res = DirectoryMapResponse(directory=dir_path, tree=tree_nodes)
        await send_tool_end_Message("ucm_directory_map", {"dir_path": dir_path, "root_path": root_path, "depth": depth, "include_symbols": include_symbols, "format_md": format_md}, res)
        return res

    @router.get("/file-map")
    @mcp.tool(description=
"""List all symbols inside a specific file
Parameters:
'file_path'
'root_path' (Optional)"""
    )
    async def ucm_file_map(file_path: str, root_path: Optional[str] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        tool_args = {"file_path": file_path, "root_path": root_path, "format_md": format_md}
        await send_tool_start_Message("ucm_file_map", tool_args)
        try:
            project_path = resolve_project(root_path)
            db_id = get_db_id(project_path)
        except ValueError as e:
            res = str(e) if format_md else [{"error": str(e)}]
            await send_tool_end_Message("ucm_file_map", tool_args, res)
            return res
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        file_path = _normalize_path(file_path)
        
        cur.execute("""
            SELECT s.id, s.name, s.type, s.line 
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE f.path = ?
            ORDER BY s.line
        """, (file_path,))
        rows = [dict(r) for r in cur.fetchall()]
        
        if format_md:
            md = [f"## Symbols in `{file_path}`"]
            if not rows:
                cur.execute("SELECT id FROM files WHERE path = ?", (file_path,))
                if not cur.fetchone():
                    import os
                    full_path = os.path.join(project_path, file_path)
                    if not os.path.exists(full_path):
                        md.append(f"- (Error: File '{file_path}' does not exist)")
                    else:
                        md.append(f"- (Error: File '{file_path}' is not indexed or unsupported format)")
                else:
                    md.append("- (No symbols found in this file)")
                res = "\n".join(md)
                await send_tool_end_Message("ucm_file_map", {"file_path": file_path, "root_path": root_path, "format_md": format_md}, res)
                return res
                
            for r in rows:
                md.append(f"- **{r['type']}** `{r['name']}` (Line {r['line']})")
            res = "\n".join(md)
            await send_tool_end_Message("ucm_file_map", {"file_path": file_path, "root_path": root_path, "format_md": format_md}, res)
            return res
        res = rows
        await send_tool_end_Message("ucm_file_map", {"file_path": file_path, "root_path": root_path, "format_md": format_md}, res)
        return res

    return router
