import re
from typing import List, Dict, Any

def extract_dotnet_routes(code_bytes: bytes, file_id: int) -> List[Dict[str, Any]]:
    content = code_bytes.decode("utf-8", errors="ignore")
    routes = []
    
    # Try to find class-level route
    base_route = ""
    class_match = re.search(r'\[Route\s*\(\s*["\']([^"\']+)["\']\s*\)\][^\{]{0,200}?class\s+([A-Za-z0-9_]+)', content)
    if class_match:
        base_route = class_match.group(1)
        controller_name = class_match.group(2)
        if controller_name.endswith("Controller"):
            controller_name = controller_name[:-10]
        base_route = base_route.replace("[controller]", controller_name)

    # Method-level routes
    attr_pattern = r'\[(Http(?:Get|Post|Put|Delete|Patch|Options|Head)|Route)\s*(?:\((.*?)\))?\s*\]'
    
    for match in re.finditer(attr_pattern, content):
        attr_name = match.group(1)
        args_str = match.group(2)
        
        path_arg = ""
        if args_str:
            arg_match = re.search(r'^\s*["\']([^"\']*)["\']', args_str)
            if arg_match:
                path_arg = arg_match.group(1)
            else:
                tpl_match = re.search(r'Template\s*=\s*["\']([^"\']*)["\']', args_str)
                if tpl_match:
                    path_arg = tpl_match.group(1)
        
        if attr_name == "Route":
            method = "ANY"
        else:
            method = attr_name[4:].upper()
            
        search_start = match.end()
        forward_text = content[search_start:search_start+500]
        
        # Clean attributes and comments to find the method name
        clean_text = re.sub(r'\[.*?\]', '', forward_text, flags=re.DOTALL)
        clean_text = re.sub(r'//.*', '', clean_text)
        clean_text = re.sub(r'/\*.*?\*/', '', clean_text, flags=re.DOTALL)
        
        m_match = re.search(r'(?:\s|^)([A-Za-z0-9_]+)(?:\s*<[^>]+>)?\s*\(', clean_text)
        if m_match:
            handler = m_match.group(1)
        else:
            handler = "UnknownMethod"
            
        final_path = path_arg or ""
        
        if final_path.startswith('/'):
            pass
        elif final_path.startswith('~/'):
            final_path = final_path[1:]
        else:
            if base_route:
                if not base_route.startswith('/'):
                    base_route = '/' + base_route
                if not base_route.endswith('/'):
                    base_route += '/'
                final_path = base_route + final_path
            else:
                if not final_path.startswith('/'):
                    final_path = '/' + final_path
                    
        final_path = re.sub(r'/+', '/', final_path)
        if final_path.endswith('/') and len(final_path) > 1:
            final_path = final_path[:-1]
            
        routes.append({
            "method": method,
            "path": final_path,
            "handler_name": handler,
            "framework": ".net"
        })
        
    return routes
