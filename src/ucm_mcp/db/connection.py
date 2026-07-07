import sqlite3
from collections import OrderedDict
from pathlib import Path

from ucm_mcp.config import get_base_dir

class ConnectionCache:
    def __init__(self, maxsize: int = 20):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, sqlite3.Connection] = OrderedDict()

    def get_connection(self, db_id: str, data_dir: str | None = None) -> sqlite3.Connection:
        if db_id in self._cache:
            self._cache.move_to_end(db_id)
            return self._cache[db_id]
            
        base_dir = get_base_dir(data_dir)
        project_dir = base_dir / "projects" / db_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        db_path = project_dir / "index.sqlite3"
        print(f"Db path from connection.py: {db_path}")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Initialize schema if new
        self._init_schema(conn)
        
        self._cache[db_id] = conn
        if len(self._cache) > self.maxsize:
            _, old_conn = self._cache.popitem(last=False)
            old_conn.close()
            
        return conn

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()

    def close_all(self):
        for conn in self._cache.values():
            conn.close()
        self._cache.clear()

_connection_cache = ConnectionCache()

def get_connection(db_id: str, data_dir: str | None = None) -> sqlite3.Connection:
    return _connection_cache.get_connection(db_id, data_dir)
