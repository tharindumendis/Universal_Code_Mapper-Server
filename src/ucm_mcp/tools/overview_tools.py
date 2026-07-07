import json
from typing import Optional, Dict, Any, List, Union
from mcp.server.fastmcp import FastMCP
from ucm_mcp.tools.project_tools import resolve_project
from ucm_mcp.identity import get_db_id
from ucm_mcp.db.repository import get_file_counts, get_total_file_count
from ucm_mcp.db.connection import get_connection

def _normalize_path(p: str) -> str:
    return p.replace("\\\\", "/").replace("\\", "/")

def register_overview_tools(mcp: FastMCP, data_dir: str | None = None) -> None:
    
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

    @mcp.tool(description="""Call when you need to list files and subdirectories within a specific directory.
    Parameters:
    'dir_path' (optional, root if omitted).
    'root_path' root path of the project.
    'depth' depth of the directory tree."""
    )
    def ucm_directory_map(dir_path: Optional[str] = None, root_path: Optional[str] = None, depth: int = 1, format_md: bool = True) -> Union[str, Dict[str, Any]]:
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

            paths = sorted([f["path"] for f in files])
            
            # Group into a tree structure
            tree = {}
            for p in paths:
                rel = p[len(dir_path):].lstrip('/')
                parts = rel.split('/')
                curr = tree
                for part in parts:
                    if part not in curr:
                        curr[part] = {}
                    curr = curr[part]
                    
            def _print_tree(node, indent_level=0):
                lines = []
                indent = "  " * indent_level
                for k in sorted(node.keys()):
                    lines.append(f"{indent}- {k}")
                    lines.extend(_print_tree(node[k], indent_level + 1))
                return lines
                
            md.extend(_print_tree(tree))
            return "\n".join(md)
        
        return {"directory": dir_path, "files": files}

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
