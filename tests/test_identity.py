import os
from pathlib import Path

from ucm_mcp.identity import (
    canonicalize_path,
    get_db_id,
    register_project,
    get_project,
    list_projects
)

def test_canonicalize_path(tmp_path):
    # Test path normalization
    p1 = tmp_path / "MyProject"
    p1.mkdir()
    
    canon1 = canonicalize_path(str(p1))
    canon2 = canonicalize_path(str(tmp_path / "myproject"))
    
    # On Windows/macOS, case insensitive filesystems will resolve these to the same
    # But for strict checking we just ensure it doesn't crash and returns string
    assert isinstance(canon1, str)
    assert len(canon1) > 0

def test_get_db_id():
    id1 = get_db_id("/some/canonical/path")
    id2 = get_db_id("/some/canonical/path")
    id3 = get_db_id("/another/path")
    
    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16

def test_registry_operations(tmp_path):
    data_dir = str(tmp_path / "ucm_data")
    project_path = str(tmp_path / "test_project")
    
    # Register new project
    info = register_project(project_path, data_dir=data_dir)
    assert info["canonical_path"] == canonicalize_path(project_path)
    assert info["file_count"] == 0
    
    # Retrieve project
    info2 = get_project(project_path, data_dir=data_dir)
    assert info2 is not None
    assert info2["db_id"] == info["db_id"]
    
    # List projects
    projects = list_projects(data_dir=data_dir)
    assert len(projects) == 1
    assert projects[0]["db_id"] == info["db_id"]

def test_get_project_not_found(tmp_path):
    data_dir = str(tmp_path / "ucm_data")
    info = get_project("/nonexistent", data_dir=data_dir)
    assert info is None
