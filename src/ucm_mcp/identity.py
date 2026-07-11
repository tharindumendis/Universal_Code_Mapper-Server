import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import TypedDict, Optional

from ucm_mcp.config import get_base_dir

class ProjectInfo(TypedDict):
    db_id: str
    canonical_path: str
    first_indexed_at: float
    last_indexed_at: Optional[float]
    file_count: int
    symbol_count: int

def canonicalize_path(path: str | Path) -> str:
    """Resolve symlinks, .. and normalize case on case-insensitive filesystems."""
    return os.path.normcase(os.path.realpath(str(path)))

def get_db_id(canonical_path: str) -> str:
    """Return the first 16 chars of sha256 hash of the canonical path."""
    return hashlib.sha256(canonical_path.encode('utf-8')).hexdigest()[:16]

def get_registry_db_path(data_dir: str | None = None) -> Path:
    base_dir = get_base_dir(data_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "registry.sqlite3"

def init_registry(db_path: Path) -> None:
    """Initialize the registry DB schema if it doesn't exist."""
    schema_path = Path(__file__).parent / "db" / "registry_schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
        
    with sqlite3.connect(db_path) as conn:
        conn.execute(schema)
        conn.commit()

def register_project(root_path: str | Path, data_dir: str | None = None) -> ProjectInfo:
    """Register or return an existing project in the registry."""
    canonical_path = canonicalize_path(root_path)
    db_id = get_db_id(canonical_path)
    db_path = get_registry_db_path(data_dir)
    init_registry(db_path)
    
    now = time.time()
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects WHERE db_id = ?", (db_id,))
        row = cur.fetchone()
        
        if row:
            return dict(row) # type: ignore
        
        cur.execute(
            """
            INSERT INTO projects (db_id, canonical_path, first_indexed_at, last_indexed_at)
            VALUES (?, ?, ?, ?)
            """,
            (db_id, canonical_path, now, None)
        )
        conn.commit()
        
        cur.execute("SELECT * FROM projects WHERE db_id = ?", (db_id,))
        row = cur.fetchone()
        return dict(row) # type: ignore

def get_project(root_path: str | Path, data_dir: str | None = None) -> Optional[ProjectInfo]:
    canonical_path = canonicalize_path(root_path)
    db_id = get_db_id(canonical_path)
    db_path = get_registry_db_path(data_dir)
    if not db_path.exists():
        return None
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects WHERE db_id = ?", (db_id,))
        row = cur.fetchone()
        if row:
            return dict(row) # type: ignore
        return None

def update_project_stats(db_id: str, file_count: int, symbol_count: int, data_dir: str | None = None) -> None:
    db_path = get_registry_db_path(data_dir)
    if not db_path.exists():
        return
        
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE projects SET file_count = ?, symbol_count = ?, last_indexed_at = ? WHERE db_id = ?",
            (file_count, symbol_count, time.time(), db_id)
        )
        conn.commit()

def list_projects(data_dir: str | None = None) -> list[ProjectInfo]:
    db_path = get_registry_db_path(data_dir)
    if not db_path.exists():
        return []
        
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects ORDER BY first_indexed_at DESC")
        rows = cur.fetchall()
        return [dict(row) for row in rows] # type: ignore
