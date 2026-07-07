import os
from pathlib import Path
from ucm_mcp.indexing.indexer import index_project_impl
from ucm_mcp.db.repository import get_file_counts, get_total_file_count

def test_index_project_impl(tmp_path):
    data_dir = str(tmp_path / "ucm_data")
    project_path = tmp_path / "my_proj"
    project_path.mkdir()
    
    # Create some dummy files
    (project_path / "main.py").write_text("print('hello')", encoding="utf-8")
    (project_path / "utils.js").write_text("console.log('world');", encoding="utf-8")
    (project_path / "README.md").write_text("docs", encoding="utf-8")
    
    # gitignore
    (project_path / ".gitignore").write_text("ignore_me.py\n", encoding="utf-8")
    (project_path / "ignore_me.py").write_text("secret", encoding="utf-8")
    
    db_id = index_project_impl(str(project_path), data_dir=data_dir)
    
    total = get_total_file_count(db_id, data_dir=data_dir)
    # main.py, utils.js, README.md, .gitignore
    assert total == 4
    
    counts = get_file_counts(db_id, data_dir=data_dir)
    assert counts.get("python") == 1
    assert counts.get("javascript") == 1
    assert counts.get("unknown") == 2 # README.md, .gitignore
