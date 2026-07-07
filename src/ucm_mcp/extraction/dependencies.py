from typing import List, Dict, Any
from tree_sitter_language_pack import get_parser

def extract_imports(code_bytes: bytes, language: str) -> List[Dict[str, Any]]:
    try:
        parser = get_parser(language)
        try:
            tree = parser.parse(code_bytes)
        except TypeError:
            tree = parser.parse(code_bytes.decode("utf-8"))
    except Exception:
        return []
        
    imports = []
    root = tree.root_node() if callable(tree.root_node) else tree.root_node
    
    def start_b(n):
        return n.start_byte() if callable(n.start_byte) else n.start_byte
    def end_b(n):
        return n.end_byte() if callable(n.end_byte) else n.end_byte
    def node_kind(n):
        return n.kind() if callable(n.kind) else n.kind
    def child_count(n):
        return n.child_count() if callable(n.child_count) else n.child_count
        
    def walk(node):
        if not node:
            return
            
        t = node_kind(node)
        c_count = child_count(node)
        
        # Python
        if t == "import_statement":
            for i in range(c_count):
                child = node.child(i)
                ckind = node_kind(child)
                if ckind == "dotted_name":
                    name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    imports.append({"to_module": name, "alias": None, "is_dynamic": False})
                elif ckind == "aliased_import":
                    name = None
                    alias = None
                    for j in range(child_count(child)):
                        sub = child.child(j)
                        skind = node_kind(sub)
                        if skind == "dotted_name":
                            name = code_bytes[start_b(sub):end_b(sub)].decode("utf-8")
                        elif skind == "identifier":
                            alias = code_bytes[start_b(sub):end_b(sub)].decode("utf-8")
                    if name:
                        imports.append({"to_module": name, "alias": alias, "is_dynamic": False})
                elif ckind == "identifier":
                    name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    if name != "import":
                        imports.append({"to_module": name, "alias": None, "is_dynamic": False})
                        
        elif t == "import_from_statement":
            module_name = None
            for i in range(c_count):
                child = node.child(i)
                if node_kind(child) == "dotted_name":
                    module_name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    break
            if module_name:
                for i in range(c_count):
                    child = node.child(i)
                    if node_kind(child) == "dotted_name" and start_b(child) > start_b(node.child(1)):
                        name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                        imports.append({"to_module": f"{module_name}.{name}", "alias": None, "is_dynamic": False})
                    elif node_kind(child) == "aliased_import":
                        name = None
                        alias = None
                        for j in range(child_count(child)):
                            sub = child.child(j)
                            if node_kind(sub) == "dotted_name":
                                name = code_bytes[start_b(sub):end_b(sub)].decode("utf-8")
                            elif node_kind(sub) == "identifier":
                                alias = code_bytes[start_b(sub):end_b(sub)].decode("utf-8")
                        if name:
                            imports.append({"to_module": f"{module_name}.{name}", "alias": alias, "is_dynamic": False})
                            
        # JS/TS
        elif t == "import_statement" and language in ("javascript", "typescript"):
            module_name = None
            for i in range(c_count):
                child = node.child(i)
                if node_kind(child) == "string":
                    module_name = code_bytes[start_b(child)+1:end_b(child)-1].decode("utf-8")
            if module_name:
                imports.append({"to_module": module_name, "alias": None, "is_dynamic": False})
                
        elif t == "call_expression" and language in ("javascript", "typescript"):
            is_require = False
            for i in range(c_count):
                child = node.child(i)
                if node_kind(child) == "identifier":
                    name = code_bytes[start_b(child):end_b(child)].decode("utf-8")
                    if name == "require":
                        is_require = True
                        break
            if is_require:
                for i in range(c_count):
                    child = node.child(i)
                    if node_kind(child) == "arguments":
                        for j in range(child_count(child)):
                            arg = child.child(j)
                            if node_kind(arg) == "string":
                                module_name = code_bytes[start_b(arg)+1:end_b(arg)-1].decode("utf-8")
                                imports.append({"to_module": module_name, "alias": None, "is_dynamic": True})
                                
        for i in range(c_count):
            walk(node.child(i))
            
    walk(root)
    return imports

def insert_imports(db_id: str, file_id: int, imports: List[Dict[str, Any]], data_dir: str | None = None) -> None:
    from ucm_mcp.db.connection import get_connection
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM imports WHERE from_file_id = ?", (file_id,))
    
    for imp in imports:
        cur.execute(
            """INSERT INTO imports (from_file_id, to_module, is_dynamic, alias)
               VALUES (?, ?, ?, ?)""",
            (file_id, imp["to_module"], imp["is_dynamic"], imp["alias"])
        )
    conn.commit()
