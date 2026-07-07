import sqlite3
from typing import TypedDict, List
from ucm_mcp.db.connection import get_connection

class FileRecord(TypedDict):
    id: int
    path: str
    language: str | None
    hash: str
    size: int
    mtime: float

def insert_or_update_file(db_id: str, path: str, language: str | None, file_hash: str, size: int, mtime: float, data_dir: str | None = None) -> tuple[int, bool]:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    
    cur.execute("SELECT id, hash FROM files WHERE path = ?", (path,))
    row = cur.fetchone()
    
    is_changed = True
    if row:
        file_id = row["id"]
        old_hash = row["hash"]
        if old_hash == file_hash:
            is_changed = False
            
        cur.execute(
            """UPDATE files SET language = ?, hash = ?, size = ?, mtime = ? WHERE id = ?""",
            (language, file_hash, size, mtime, file_id)
        )
    else:
        cur.execute(
            """INSERT INTO files (path, language, hash, size, mtime) VALUES (?, ?, ?, ?, ?)""",
            (path, language, file_hash, size, mtime)
        )
        file_id = cur.lastrowid
        
    conn.commit()
    assert file_id is not None
    return file_id, is_changed

def get_file_counts(db_id: str, data_dir: str | None = None) -> dict[str, int]:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    cur.execute("SELECT language, COUNT(*) as count FROM files GROUP BY language")
    rows = cur.fetchall()
    
    result = {}
    for row in rows:
        lang = row["language"] or "unknown"
        result[lang] = row["count"]
    return result

def get_total_file_count(db_id: str, data_dir: str | None = None) -> int:
    conn = get_connection(db_id, data_dir)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM files")
    return cur.fetchone()["c"]
