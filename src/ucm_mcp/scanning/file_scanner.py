import hashlib
import os
from pathlib import Path
from typing import Iterator, Tuple
import pathspec

def get_ignore_spec(root_path: Path) -> pathspec.PathSpec:
    patterns = [".git/", "node_modules/", "__pycache__/", "venv/", ".venv/", "*.sqlite3", "bin/", "obj/", "build/", "dist/", ".idea/", ".vscode/", "cache/", ".next/", ".vs"]
    gitignore_path = root_path / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            patterns.extend(f.readlines())
    return pathspec.PathSpec.from_lines('gitignore', patterns)

def scan_files(root_path: Path) -> Iterator[Tuple[str, int, float, str]]:
    """Yields (rel_path, size, mtime, hash)."""
    spec = get_ignore_spec(root_path)
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        print(f"In loop dirpath: {dirpath}, dirnames: {dirnames}, filenames: {filenames}")
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == ".":
            rel_dir = ""
            
        # Filter directories in-place
        dirnames[:] = [d for d in dirnames if not spec.match_file(os.path.join(rel_dir, d).replace("\\", "/") + "/")]
        
        for filename in filenames:
            rel_file = os.path.join(rel_dir, filename).replace("\\", "/")
            if spec.match_file(rel_file):
                continue
                
            full_path = Path(dirpath) / filename
            if not full_path.is_file():
                continue
                
            try:
                stat = full_path.stat()
                size = stat.st_size
                mtime = stat.st_mtime
                with open(full_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                yield rel_file, size, mtime, file_hash
            except (OSError, PermissionError):
                continue
