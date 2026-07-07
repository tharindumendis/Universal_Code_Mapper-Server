import os
from pathlib import Path
from typing import List, TypedDict, Optional
from ucm_mcp.parsing.engine import parse, get_query
from ucm_mcp.db.connection import get_connection

class Symbol(TypedDict):
    type: str
    name: str
    line: int
    column: int
    signature: Optional[str]
    docstring: Optional[str]
    summary: Optional[str]

def load_query(language: str) -> str | None:
    query_file = Path(__file__).parent.parent / "parsing" / "queries" / f"{language}_symbols.scm"
    if query_file.exists():
        with open(query_file, "r", encoding="utf-8") as f:
            return f.read()
    return None

def extract_symbols(code_bytes: bytes, language: str) -> List[Symbol]:
    tree = parse(code_bytes, language)
    
    symbols = []
    root = tree.root_node() if callable(tree.root_node) else tree.root_node
    
    def walk(node):
        if not node:
            return
            
        t = node.kind() if callable(node.kind) else node.kind
        child_count = node.child_count() if callable(node.child_count) else node.child_count
        
        # Helper accessors
        def start_pos(n):
            return n.start_position() if callable(n.start_position) else n.start_position
        def start_b(n):
            return n.start_byte() if callable(n.start_byte) else n.start_byte
        def end_b(n):
            return n.end_byte() if callable(n.end_byte) else n.end_byte
        def node_kind(n):
            return n.kind() if callable(n.kind) else n.kind
        def get_row(p):
            return p.row if hasattr(p, 'row') else p[0]
        def get_col(p):
            return p.column if hasattr(p, 'column') else p[1]
            
        # Python
        if t in ("class_definition", "function_definition"):
            name_node = None
            for i in range(child_count):
                child = node.child(i)
                if node_kind(child) == "identifier":
                    name_node = child
                    break
            if name_node:
                sym_type = "class" if t == "class_definition" else "function"
                name_text = code_bytes[start_b(name_node):end_b(name_node)].decode("utf-8")
                pos = start_pos(node)
                symbols.append({
                    "type": sym_type,
                    "name": name_text,
                    "line": get_row(pos) + 1,
                    "column": get_col(pos),
                    "signature": "",
                    "docstring": "",
                    "summary": ""
                })
                
        # JavaScript / TypeScript
        if t in ("class_declaration", "function_declaration", "method_definition"):
            name_node = None
            for i in range(child_count):
                child = node.child(i)
                if node_kind(child) in ("identifier", "property_identifier"):
                    name_node = child
                    break
            if name_node:
                sym_type = "class"
                if t == "function_declaration": sym_type = "function"
                if t == "method_definition": sym_type = "method"
                name_text = code_bytes[start_b(name_node):end_b(name_node)].decode("utf-8")
                pos = start_pos(node)
                symbols.append({
                    "type": sym_type,
                    "name": name_text,
                    "line": get_row(pos) + 1,
                    "column": get_col(pos),
                    "signature": "",
                    "docstring": "",
                    "summary": ""
                })
                
        # Java / C#
        if t in ("class_declaration", "method_declaration"):
            name_node = None
            for i in range(child_count):
                child = node.child(i)
                if node_kind(child) == "identifier":
                    name_node = child
                    break
            if name_node:
                sym_type = "class" if t == "class_declaration" else "method"
                name_text = code_bytes[start_b(name_node):end_b(name_node)].decode("utf-8")
                pos = start_pos(node)
                symbols.append({
                    "type": sym_type,
                    "name": name_text,
                    "line": get_row(pos) + 1,
                    "column": get_col(pos),
                    "signature": "",
                    "docstring": "",
                    "summary": ""
                })
                
        for i in range(child_count):
            walk(node.child(i))
                
    walk(root)
    return symbols

def insert_symbols(db_id: str, file_id: int, symbols: List[Symbol], data_dir: str | None = None) -> None:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
    
    for sym in symbols:
        cur.execute(
            """INSERT INTO symbols (file_id, type, name, line, column, signature, docstring, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (file_id, sym["type"], sym.get("name", ""), sym["line"], sym["column"], sym.get("signature"), sym.get("docstring"), sym.get("summary"))
        )
    conn.commit()
