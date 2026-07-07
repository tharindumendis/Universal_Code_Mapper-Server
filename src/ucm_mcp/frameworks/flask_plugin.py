import re
from typing import List, Dict, Any

def extract_flask_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches @app.route('/path') or @blueprint.route('/path')
    # Followed by a function definition (def my_handler():)
    pattern = r'@(?:[A-Za-z0-9_]+)\.route\s*\(\s*[\'"]([^\'"]+)[\'"][^)]*\)\s*def\s+([A-Za-z0-9_]+)\s*\('
    for match in re.finditer(pattern, content):
        url = match.group(1)
        handler = match.group(2)
        
        routes.append({
            "method": "ANY",
            "path": url,
            "handler_name": handler,
            "framework": "flask"
        })
        
    return routes
