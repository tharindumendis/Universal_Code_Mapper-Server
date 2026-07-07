import re
from typing import List, Dict, Any

def extract_angular_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches { path: 'path', component: ComponentName }
    pattern = r'\{\s*path\s*:\s*[\'"]([^\'"]+)[\'"][^}]*?component\s*:\s*([A-Za-z0-9_]+)'
    for match in re.finditer(pattern, content):
        url = match.group(1)
        if not url.startswith('/'):
            url = '/' + url
        handler = match.group(2)
        
        routes.append({
            "method": "GET", # Angular routes are frontend routes, usually GET
            "path": url,
            "handler_name": handler,
            "framework": "angular"
        })
        
    return routes
