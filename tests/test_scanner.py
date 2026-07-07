from pathlib import Path
from ucm_mcp.scanning.language_detect import detect_language

def test_language_detect():
    assert detect_language("app.py") == "python"
    assert detect_language("src/main.js") == "javascript"
    assert detect_language("unknown.xyz") is None
    assert detect_language("test.TSX") == "typescript"
