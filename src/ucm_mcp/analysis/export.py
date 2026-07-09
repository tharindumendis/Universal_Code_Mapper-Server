from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from ucm_mcp.db.connection import get_connection

class Node(BaseModel):
    id: str
    type: str
    label: str
    parent: Optional[str] = None
    language: Optional[str] = None
    symbol_type: Optional[str] = None
    line: Optional[int] = None
    framework: Optional[str] = None

class Edge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: Optional[str] = None

class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

def get_full_graph(db_id: str, data_dir: Optional[str] = None) -> GraphData:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
    if not cur.fetchone():
        raise ValueError("Project not indexed")

    
    nodes: List[Node] = []
    edges: List[Edge] = []
    
    # 1. Add a central root node for the project
    nodes.append(Node(id="dir_root", type="dir", label="Project Root", parent=None))
    
    # 2. Get all files and build directory nodes
    cur.execute("SELECT id, path, language FROM files")
    files = cur.fetchall()
    seen_dirs = {"dir_root"}
    
    for f in files:
        path = f['path']
        parts = path.split('/')
        file_name = parts[-1]
        
        parent_id = "dir_root"
        current_dir_path = ""
        for i in range(len(parts) - 1):
            part = parts[i]
            if current_dir_path:
                current_dir_path += f"/{part}"
            else:
                current_dir_path = part
                
            dir_id = f"dir_{current_dir_path}"
            if dir_id not in seen_dirs:
                seen_dirs.add(dir_id)
                nodes.append(Node(
                    id=dir_id,
                    type="dir",
                    label=part,
                    parent=parent_id
                ))
            parent_id = dir_id

        nodes.append(Node(
            id=f"file_{f['id']}",
            type="file",
            label=file_name,
            language=f['language'],
            parent=parent_id
        ))
        
    # 2. Get all symbols
    cur.execute("SELECT id, file_id, type, name, line FROM symbols")
    symbols = cur.fetchall()
    for s in symbols:
        nodes.append(Node(
            id=f"sym_{s['id']}",
            type="symbol",
            label=s['name'],
            symbol_type=s['type'],
            line=s['line'],
            parent=f"file_{s['file_id']}"
        ))
        
    # 3. Get all routes
    cur.execute("""
        SELECT r.id, r.method, r.path, r.handler_symbol_id, r.framework, s.file_id 
        FROM routes r
        LEFT JOIN symbols s ON r.handler_symbol_id = s.id
    """)
    routes = cur.fetchall()
    for r in routes:
        parent_id = f"file_{r['file_id']}" if r['file_id'] else None
        nodes.append(Node(
            id=f"route_{r['id']}",
            type="route",
            label=f"{r['method']} {r['path']}",
            framework=r['framework'],
            parent=parent_id
        ))
        # Edge: Route -> Handler
        if r['handler_symbol_id']:
            edges.append(Edge(
                id=f"edge_r2h_{r['id']}",
                source=f"route_{r['id']}",
                target=f"sym_{r['handler_symbol_id']}",
                type="handled_by"
            ))
            
    # 4. Get all imports (File -> File)
    cur.execute("SELECT id, from_file_id, resolved_file_id, to_module FROM imports WHERE resolved_file_id IS NOT NULL")
    imports = cur.fetchall()
    for i in imports:
        edges.append(Edge(
            id=f"edge_imp_{i['id']}",
            source=f"file_{i['from_file_id']}",
            target=f"file_{i['resolved_file_id']}",
            type="imports",
            label=i['to_module']
        ))
        
    # 5. Get all calls (Symbol -> Symbol)
    cur.execute("SELECT id, caller_symbol_id, callee_symbol_id, callee_name FROM calls WHERE callee_symbol_id IS NOT NULL")
    calls = cur.fetchall()
    for c in calls:
        edges.append(Edge(
            id=f"edge_call_{c['id']}",
            source=f"sym_{c['caller_symbol_id']}",
            target=f"sym_{c['callee_symbol_id']}",
            type="calls",
            label=c['callee_name']
        ))
        
    # 6. Get all inheritance
    cur.execute("SELECT id, child_symbol_id, parent_symbol_id, kind FROM inheritance WHERE parent_symbol_id IS NOT NULL")
    inheritances = cur.fetchall()
    for ih in inheritances:
        edges.append(Edge(
            id=f"edge_inh_{ih['id']}",
            source=f"sym_{ih['child_symbol_id']}",
            target=f"sym_{ih['parent_symbol_id']}",
            type=ih['kind']
        ))
        
    return GraphData(nodes=nodes, edges=edges)
