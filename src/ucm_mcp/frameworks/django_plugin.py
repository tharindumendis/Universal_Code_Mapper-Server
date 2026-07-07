import re
from typing import List, Dict, Any

def extract_django_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Very basic regex for path('url', view, name='...')
    # Matches path("...", view) or re_path("...", view)
    pattern = r'(?:path|re_path)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([A-Za-z0-9_\.]+)'
    for match in re.finditer(pattern, content):
        url = match.group(1)
        handler = match.group(2)
        if handler.endswith('.as_view'):
            handler = handler[:-8]
            
        routes.append({
            "method": "ANY",
            "path": url,
            "handler_name": handler,
            "framework": "django"
        })
        
    return routes
