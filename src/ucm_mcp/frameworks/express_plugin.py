import re
from typing import List, Dict, Any

def extract_express_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches app.get('/path', handler) or router.post('/path', handler)
    pattern = r'(?:[A-Za-z0-9_]+)\.(get|post|put|delete|patch|all)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([A-Za-z0-9_]+)?'
    for match in re.finditer(pattern, content):
        method = match.group(1).upper()
        if method == "ALL":
            method = "ANY"
        url = match.group(2)
        handler = match.group(3) or "AnonymousHandler"
        
        routes.append({
            "method": method,
            "path": url,
            "handler_name": handler,
            "framework": "express"
        })
        
    return routes
