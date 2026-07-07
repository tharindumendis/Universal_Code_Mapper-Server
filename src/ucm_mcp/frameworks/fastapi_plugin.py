import re
from typing import List, Dict, Any

def extract_fastapi_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches @app.get('/path') or @router.post('/path')
    # Followed by a function definition (def my_handler(): or async def my_handler():)
    pattern = r'@(?:[A-Za-z0-9_]+)\.(get|post|put|delete|patch|options|head|trace)\s*\(\s*[\'"]([^\'"]+)[\'"][^)]*\)\s*(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\('
    for match in re.finditer(pattern, content):
        method = match.group(1).upper()
        url = match.group(2)
        handler = match.group(3)
        
        routes.append({
            "method": method,
            "path": url,
            "handler_name": handler,
            "framework": "fastapi"
        })
        
    return routes
