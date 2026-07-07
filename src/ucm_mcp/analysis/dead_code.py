from typing import List, Dict, Any
from ucm_mcp.db.connection import get_connection

def find_dead_code(db_id: str, symbol_types: List[str] | None, data_dir: str | None = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    # We find symbols that never appear as a callee_name in `calls`
    # and maybe filter by symbol_types (like ['function', 'method'])
    
    sql = '''
        SELECT s.name, s.type, f.path, s.line
        FROM symbols s
        JOIN files f ON s.file_id = f.id
        WHERE s.name NOT IN (SELECT callee_name FROM calls)
    '''
    params = []
    
    if symbol_types:
        placeholders = ",".join("?" for _ in symbol_types)
        sql += f" AND s.type IN ({placeholders})"
        params.extend(symbol_types)
        
    # Also ignore standard dunder methods in Python, etc.
    sql += " AND s.name NOT LIKE '\\_\\_%' ESCAPE '\\'"
    
    # Ignore test functions
    sql += " AND s.name NOT LIKE 'test_%'"
    
    sql += " ORDER BY f.path, s.line"
    
    cur.execute(sql, tuple(params))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "name": row["name"],
            "type": row["type"],
            "path": row["path"],
            "line": row["line"]
        })
        
    return results
