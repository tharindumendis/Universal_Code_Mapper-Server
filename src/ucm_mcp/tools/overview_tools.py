import json
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter
from fastmcp import FastMCP
from ucm_mcp.tools.project_tools import resolve_project
from ucm_mcp.identity import get_db_id
from pydantic import BaseModel
from ucm_mcp.db.repository import get_file_counts, get_total_file_count
from ucm_mcp.db.connection import get_connection

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
    @mcp.tool(description="""Call when you need a high-level overview of the project, including file counts and language breakdown.
    Parameters:
    'root_path' root path of the project."""
    )
    def ucm_project_overview(root_path: Optional[str] = None, format_md: bool = True) -> Union[str, Dict[str, Any]]:
        project_path = resolve_project(root_path)
        db_id = get_db_id(project_path)
        
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
            return "\n".join(md)
        return res

    @router.get("/directory-map")
    @mcp.tool(description="""Call when you need to list files and subdirectories within a specific directory.
    Parameters:
    'dir_path' (optional, root if omitted).
    'root_path' root path of the project.
    'depth' depth of the directory tree.
    'include_symbols' whether to include symbols (functions/classes) as children of files (default True)."""
    )
    def ucm_directory_map(dir_path: Optional[str] = None, root_path: Optional[str] = None, depth: int = 1, include_symbols: bool = True, format_md: bool = True) -> Union[str, DirectoryMapResponse]:
        project_path = resolve_project(root_path)
        db_id = get_db_id(project_path)
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
                return "\n".join(md)
            
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
            return "\n".join(md)
        
        return DirectoryMapResponse(directory=dir_path, tree=tree_nodes)

    @router.get("/file-map")
    @mcp.tool(description="""Call when you need to list all symbols (functions, classes, variables) inside a specific file.
    Parameters:
    'file_path' path of the file.
    'root_path' root path of the project."""
    )
    def ucm_file_map(file_path: str, root_path: Optional[str] = None, format_md: bool = True) -> Union[str, List[Dict[str, Any]]]:
        project_path = resolve_project(root_path)
        db_id = get_db_id(project_path)
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
                return "\n".join(md)
                
            for r in rows:
                md.append(f"- **{r['type']}** `{r['name']}` (Line {r['line']})")
            return "\n".join(md)
        return rows

    return router
