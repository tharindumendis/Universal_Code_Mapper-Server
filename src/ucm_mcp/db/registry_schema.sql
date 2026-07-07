CREATE TABLE IF NOT EXISTS projects (
    db_id TEXT PRIMARY KEY,
    canonical_path TEXT UNIQUE NOT NULL,
    first_indexed_at REAL NOT NULL,
    last_indexed_at REAL,
    file_count INTEGER DEFAULT 0,
    symbol_count INTEGER DEFAULT 0
);
