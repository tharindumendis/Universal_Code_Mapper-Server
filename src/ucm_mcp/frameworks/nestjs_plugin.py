import re
from typing import List, Dict, Any

def extract_nestjs_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Matches controller-level route: @Controller('path')
    # and method-level route: @Get('path'), @Post('path'), etc.
    # We will just extract method-level routes for simplicity, or we can try to find controller base paths.
    
    # Find all controllers and their base paths
    controller_pattern = r'@Controller\s*\(\s*[\'"]([^\'"]*)[\'"]\s*\)\s*(?:export\s+)?class\s+([A-Za-z0-9_]+)'
    controllers = {}
    for match in re.finditer(controller_pattern, content):
        base_path = match.group(1)
        if not base_path.startswith('/'):
            base_path = '/' + base_path
        controllers[match.end()] = base_path # we can use position if needed, but it's complex. Let's just assume one controller per file for simplicity.
        
    base_path = ""
    if controllers:
        # Just take the first controller's base path for the whole file
        base_path = list(controllers.values())[0]
        if base_path == '/':
            base_path = ""
            
    # Matches @Get('path'), @Post('path'), etc. followed by method definition
    method_pattern = r'@(Get|Post|Put|Delete|Patch|Options|Head|All)\s*\(\s*(?:[\'"]([^\'"]*)[\'"])?\s*\)[^@]*?(?:async\s+)?([A-Za-z0-9_]+)\s*\('
    for match in re.finditer(method_pattern, content):
        method = match.group(1).upper()
        if method == "ALL":
            method = "ANY"
            
        sub_path = match.group(2) or ""
        if sub_path and not sub_path.startswith('/'):
            sub_path = '/' + sub_path
            
        handler = match.group(3)
        
        full_path = base_path + sub_path
        if not full_path:
            full_path = "/"
            
        routes.append({
            "method": method,
            "path": full_path,
            "handler_name": handler,
            "framework": "nestjs"
        })
        
    return routes
