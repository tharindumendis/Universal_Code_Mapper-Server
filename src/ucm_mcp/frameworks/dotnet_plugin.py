import re
from typing import List, Dict, Any

def extract_dotnet_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches [HttpGet("path")] or [Route("path")] followed by method definition
    # e.g., public async Task<IActionResult> GetMyData()
    pattern = r'\[(?:Http)?(Get|Post|Put|Delete|Patch|Route)\s*\(\s*[\'"]([^\'"]*)[\'"][^\]]*\)\][^\[]*?(?:public|private|protected)?\s*(?:(?:async\s+)?(?:Task<[^>]+>|[A-Za-z0-9_<>]+)\s+)([A-Za-z0-9_]+)\s*\('
    for match in re.finditer(pattern, content):
        method = match.group(1).upper()
        if method == "ROUTE":
            method = "ANY"
            
        url = match.group(2)
        if not url.startswith('/'):
            url = '/' + url
            
        handler = match.group(3)
        
        routes.append({
            "method": method,
            "path": url,
            "handler_name": handler,
            "framework": ".net"
        })
        
    return routes
