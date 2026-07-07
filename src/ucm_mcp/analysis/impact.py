from typing import List, Dict, Any, Set
from ucm_mcp.db.connection import get_connection

def calculate_impact(db_id: str, symbol_name: str, depth: int, data_dir: str | None = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    # We find all symbols that call this symbol (directly or indirectly) up to 'depth' levels.
    # Because we don't have a CTE (Common Table Expression) for recursion easily accessible if we just want simple Python logic,
    # we can do it iteratively.
    
    affected_symbols = set()
    current_level_names = {symbol_name}
    
    for _ in range(depth):
        if not current_level_names:
            break
            
        placeholders = ",".join("?" for _ in current_level_names)
        cur.execute(f'''
            SELECT s.name, s.type, f.path
            FROM calls c
            JOIN symbols s ON c.caller_symbol_id = s.id
            JOIN files f ON s.file_id = f.id
            WHERE c.callee_name IN ({placeholders})
        ''', list(current_level_names))
        
        next_level = set()
        for row in cur.fetchall():
            sym_desc = f"{row['type']} {row['name']} ({row['path']})"
            if sym_desc not in affected_symbols:
                affected_symbols.add(sym_desc)
                next_level.add(row['name'])
                
        current_level_names = next_level
        
    return list(affected_symbols)
