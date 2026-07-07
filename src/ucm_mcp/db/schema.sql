CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    language TEXT,
    hash TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    type TEXT NOT NULL,          
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES symbols(id),
    visibility TEXT,
    line INTEGER NOT NULL,
    column INTEGER NOT NULL,
    signature TEXT,
    docstring TEXT,
    summary TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
    name, docstring, summary,
    content='symbols', content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);

CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
  INSERT INTO symbols_fts(rowid, name, docstring, summary) VALUES (new.id, new.name, new.docstring, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
  INSERT INTO symbols_fts(symbols_fts, rowid, name, docstring, summary) VALUES ('delete', old.id, old.name, old.docstring, old.summary);
END;
CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols BEGIN
  INSERT INTO symbols_fts(symbols_fts, rowid, name, docstring, summary) VALUES ('delete', old.id, old.name, old.docstring, old.summary);
  INSERT INTO symbols_fts(rowid, name, docstring, summary) VALUES (new.id, new.name, new.docstring, new.summary);
END;

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    from_file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    to_module TEXT NOT NULL,
    resolved_file_id INTEGER REFERENCES files(id),
    is_dynamic BOOLEAN DEFAULT 0,
    alias TEXT
);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY,
    caller_symbol_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    callee_symbol_id INTEGER REFERENCES symbols(id),
    callee_name TEXT NOT NULL,
    line INTEGER
);

CREATE TABLE IF NOT EXISTS refs (
    id INTEGER PRIMARY KEY,
    symbol_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    line INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inheritance (
    id INTEGER PRIMARY KEY,
    child_symbol_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    parent_symbol_id INTEGER REFERENCES symbols(id),
    parent_name TEXT NOT NULL,
    kind TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_symbol_id);
CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_symbol_id);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    handler_symbol_id INTEGER REFERENCES symbols(id) ON DELETE CASCADE,
    framework TEXT
);
