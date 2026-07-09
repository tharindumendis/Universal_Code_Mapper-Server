from typing import List, Dict, Any
from tree_sitter_language_pack import get_parser

def extract_calls(code_bytes: bytes, language: str) -> List[Dict[str, Any]]:
    try:
        parser = get_parser(language)
        try:
            tree = parser.parse(code_bytes)
        except TypeError:
            tree = parser.parse(code_bytes.decode("utf-8"))
    except Exception as e:
        from ucm_mcp.logger import get_logger
        get_logger(__name__).exception(f"Error extracting calls: {e}")
        return []
        
    calls = []
    root = tree.root_node() if callable(tree.root_node) else tree.root_node
    
    def start_pos(n):
        if hasattr(n, 'start_point'): return n.start_point() if callable(n.start_point) else n.start_point
        if hasattr(n, 'start_position'): return n.start_position() if callable(n.start_position) else n.start_position
        return (0, 0)
    def start_b(n):
        return n.start_byte() if callable(getattr(n, 'start_byte', None)) else getattr(n, 'start_byte', 0)
    def end_b(n):
        return n.end_byte() if callable(getattr(n, 'end_byte', None)) else getattr(n, 'end_byte', 0)
    def node_kind(n):
        if hasattr(n, 'type'): return n.type() if callable(n.type) else n.type
        if hasattr(n, 'kind'): return n.kind() if callable(n.kind) else n.kind
        return None
    def child_count(n):
        if hasattr(n, 'child_count'): return n.child_count() if callable(n.child_count) else n.child_count
        if hasattr(n, 'children'): return len(n.children)
        return 0
    def get_child(n, i):
        if hasattr(n, 'children'): return n.children[i]
        return n.child(i) if callable(n.child) else n.child[i]
    def get_row(p):
        return p.row if hasattr(p, 'row') else p[0]
        
    def walk(node):
        if not node:
            return
            
        t = node_kind(node)
        c_count = child_count(node)
        
        # Python
        if t == "call":
            for i in range(c_count):
                child = get_child(node, i)
                ckind = node_kind(child)
                # The first child is usually the function/method being called
                if ckind in ("identifier", "attribute"):
                    callee = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    pos = start_pos(node)
                    calls.append({"callee_name": callee, "line": get_row(pos) + 1})
                    break
                    
        # JS/TS
        elif t == "call_expression" and language in ("javascript", "typescript"):
            for i in range(c_count):
                child = get_child(node, i)
                ckind = node_kind(child)
                if ckind in ("identifier", "member_expression"):
                    callee = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    if callee == "require":
                        break # handled by dependencies
                    pos = start_pos(node)
                    calls.append({"callee_name": callee, "line": get_row(pos) + 1})
                    break
                    
        for i in range(c_count):
            walk(get_child(node, i))
            
    walk(root)
    return calls

def insert_calls(db_id: str, file_id: int, calls: List[Dict[str, Any]], data_dir: str | None = None) -> None:
    from ucm_mcp.db.connection import get_connection
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    # First, get all symbols in this file to map lines to caller_symbol_id
    cur.execute("SELECT id, line FROM symbols WHERE file_id = ? ORDER BY line ASC", (file_id,))
    symbols = cur.fetchall()
    
    def get_caller_id(line: int) -> int | None:
        best_id = None
        for sym in symbols:
            if sym["line"] <= line:
                best_id = sym["id"]
            else:
                break
        return best_id
    
    # Clean up old calls (we need a way to delete them. Usually we delete by caller_symbol_id,
    # but we can also just delete all calls originating from symbols in this file).
    if symbols:
        symbol_ids = [s["id"] for s in symbols]
        placeholders = ",".join("?" for _ in symbol_ids)
        cur.execute(f"DELETE FROM calls WHERE caller_symbol_id IN ({placeholders})", symbol_ids)
        
        for call in calls:
            caller_id = get_caller_id(call["line"])
            if caller_id is not None:
                cur.execute(
                    """INSERT INTO calls (caller_symbol_id, callee_name, line)
                       VALUES (?, ?, ?)""",
                    (caller_id, call["callee_name"], call["line"])
                )
    conn.commit()
