import re
from typing import List, Dict, Any

def extract_react_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Basic regex for <Route path="..." element={<Comp />} /> or component={Comp}
    pattern = r'<Route[^>]*?path=[\'"]([^\'"]+)[\'"][^>]*?(?:element=\{<([A-Za-z0-9_]+)|component=\{([A-Za-z0-9_]+))'
    for match in re.finditer(pattern, content):
        url = match.group(1)
        handler = match.group(2) or match.group(3)
        if handler:
            routes.append({
                "method": "GET",
                "path": url,
                "handler_name": handler,
                "framework": "react"
            })
            
    return routes
