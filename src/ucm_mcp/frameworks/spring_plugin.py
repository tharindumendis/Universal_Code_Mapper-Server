import re
from typing import List, Dict, Any

def extract_spring_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches controller-level route: @RequestMapping("/api/v1") or @RequestMapping(value = "/api")
    # Actually, let's just find all @GetMapping, @PostMapping etc.
    # To properly get the base path we need to find @RequestMapping on a class, but for simplicity
    # we'll look for @RestController or @Controller with a @RequestMapping.
    
    # Simple method-level matching:
    # @GetMapping("/path")
    # @RequestMapping(value="/path", method=RequestMethod.GET)
    
    # Let's use a simpler regex for the common cases: @(Get|Post|Put|Delete|Patch|Mapping)(Mapping)?("/path")
    method_pattern = r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?[\'"]([^\'"]*)[\'"][^)]*\)[^@]*?(?:public|private|protected)?\s*(?:[A-Za-z0-9_<>\[\]]+\s+)+([A-Za-z0-9_]+)\s*\('
    for match in re.finditer(method_pattern, content):
        method = match.group(1).upper()
        if method == "REQUEST":
            method = "ANY"
            
        url = match.group(2)
        if not url.startswith('/'):
            url = '/' + url
            
        handler = match.group(3)
        
        routes.append({
            "method": method,
            "path": url,
            "handler_name": handler,
            "framework": "spring"
        })
        
    return routes
