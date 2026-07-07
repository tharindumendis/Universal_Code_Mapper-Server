from typing import List, Dict, Any
from tree_sitter_language_pack import get_parser

def extract_inheritance(code_bytes: bytes, language: str) -> List[Dict[str, Any]]:
    try:
        parser = get_parser(language)
        try:
            tree = parser.parse(code_bytes)
        except TypeError:
            tree = parser.parse(code_bytes.decode("utf-8"))
    except Exception:
        return []
        
    inheritance_list = []
    root = tree.root_node() if callable(tree.root_node) else tree.root_node
    
    def start_pos(n):
        return n.start_position() if callable(n.start_position) else n.start_position
    def start_b(n):
        return n.start_byte() if callable(n.start_byte) else n.start_byte
    def end_b(n):
        return n.end_byte() if callable(n.end_byte) else n.end_byte
    def node_kind(n):
        return n.kind() if callable(n.kind) else n.kind
    def child_count(n):
        return n.child_count() if callable(n.child_count) else n.child_count
    def get_row(p):
        return p.row if hasattr(p, 'row') else p[0]
        
    def walk(node):
        if not node:
            return
            
        t = node_kind(node)
        c_count = child_count(node)
        
        # Python
        if t == "class_definition":
            class_name = None
            for i in range(c_count):
                child = node.child(i)
                ckind = node_kind(child)
                if ckind == "identifier":
                    class_name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    break
            
            if class_name:
                for i in range(c_count):
                    child = node.child(i)
                    ckind = node_kind(child)
                    if ckind == "argument_list":
                        for j in range(child_count(child)):
                            arg = child.child(j)
                            akind = node_kind(arg)
                            if akind in ("identifier", "attribute"):
                                parent_name = code_bytes[start_b(arg):end_b(arg)].decode("utf-8")
                                pos = start_pos(node)
                                inheritance_list.append({
                                    "child_name": class_name, 
                                    "parent_name": parent_name, 
                                    "kind": "extends",
                                    "line": get_row(pos) + 1
                                })
                                
        # JS/TS
        elif t == "class_declaration" and language in ("javascript", "typescript"):
            class_name = None
            for i in range(c_count):
                child = node.child(i)
                ckind = node_kind(child)
                if ckind == "identifier":
                    class_name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    break
                    
            if class_name:
                for i in range(c_count):
                    child = node.child(i)
                    ckind = node_kind(child)
                    if ckind == "class_heritage":
                        for j in range(child_count(child)):
                            arg = child.child(j)
                            akind = node_kind(arg)
                            if akind in ("identifier", "member_expression"):
                                parent_name = code_bytes[start_b(arg):end_b(arg)].decode("utf-8")
                                pos = start_pos(node)
                                inheritance_list.append({
                                    "child_name": class_name, 
                                    "parent_name": parent_name, 
                                    "kind": "extends",
                                    "line": get_row(pos) + 1
                                })
                                
        for i in range(c_count):
            walk(node.child(i))
            
    walk(root)
    return inheritance_list

def insert_inheritance(db_id: str, file_id: int, inheritances: List[Dict[str, Any]], data_dir: str | None = None) -> None:
    from ucm_mcp.db.connection import get_connection
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    # First, get all symbols in this file to map child_name + line to child_symbol_id
    cur.execute("SELECT id, name, line FROM symbols WHERE file_id = ? AND type = 'class'", (file_id,))
    symbols = cur.fetchall()
    
    def get_child_id(name: str, line: int) -> int | None:
        best_id = None
        for sym in symbols:
            # inheritance line should exactly match or be close to the class line
            if sym["name"] == name and sym["line"] <= line:
                best_id = sym["id"]
        return best_id
        
    if symbols:
        symbol_ids = [s["id"] for s in symbols]
        placeholders = ",".join("?" for _ in symbol_ids)
        cur.execute(f"DELETE FROM inheritance WHERE child_symbol_id IN ({placeholders})", symbol_ids)
        
        for inh in inheritances:
            child_id = get_child_id(inh["child_name"], inh["line"])
            if child_id is not None:
                cur.execute(
                    """INSERT INTO inheritance (child_symbol_id, parent_name, kind)
                       VALUES (?, ?, ?)""",
                    (child_id, inh["parent_name"], inh["kind"])
                )
    conn.commit()
