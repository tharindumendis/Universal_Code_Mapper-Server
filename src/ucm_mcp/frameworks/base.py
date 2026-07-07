from typing import List, Dict, Any

def insert_routes(db_id: str, file_id: int, routes: List[Dict[str, Any]], data_dir: str | None = None) -> None:
    from ucm_mcp.db.connection import get_connection
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    # Get symbols to map handler_name to handler_symbol_id
    cur.execute("SELECT id, name FROM symbols WHERE file_id = ?", (file_id,))
    symbols = {row["name"]: row["id"] for row in cur.fetchall()}
    
    cur.execute("DELETE FROM routes WHERE file_id = ?", (file_id,))
    
    for route in routes:
        handler_name = route.get("handler_name")
        handler_id = symbols.get(handler_name) if handler_name else None
        
        cur.execute(
            """INSERT INTO routes (file_id, method, path, handler_symbol_id, framework)
               VALUES (?, ?, ?, ?, ?)""",
            (file_id, route["method"], route["path"], handler_id, route["framework"])
        )
    conn.commit()
