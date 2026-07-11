import os
from pathlib import Path
from ucm_mcp.identity import register_project
from ucm_mcp.scanning.file_scanner import scan_files
from ucm_mcp.scanning.language_detect import detect_language
from ucm_mcp.db.repository import insert_or_update_file

from ucm_mcp.extraction.symbols import extract_symbols, insert_symbols
from ucm_mcp.extraction.dependencies import extract_imports, insert_imports
from ucm_mcp.extraction.calls import extract_calls, insert_calls
from ucm_mcp.extraction.inheritance import extract_inheritance, insert_inheritance
from ucm_mcp.frameworks.django_plugin import extract_django_routes
from ucm_mcp.frameworks.flask_plugin import extract_flask_routes
from ucm_mcp.frameworks.fastapi_plugin import extract_fastapi_routes
from ucm_mcp.frameworks.react_plugin import extract_react_routes
from ucm_mcp.frameworks.express_plugin import extract_express_routes
from ucm_mcp.frameworks.nestjs_plugin import extract_nestjs_routes
from ucm_mcp.frameworks.vue_router_plugin import extract_vue_routes
from ucm_mcp.frameworks.angular_plugin import extract_angular_routes
from ucm_mcp.frameworks.spring_plugin import extract_spring_routes
from ucm_mcp.frameworks.dotnet_plugin import extract_dotnet_routes
from ucm_mcp.frameworks.base import insert_routes
import threading
from watchfiles import watch
from ucm_mcp.logger import get_logger

logger = get_logger(__name__)

_WATCHERS = {}

def _start_watcher(root_path: str, db_id: str, data_dir: str | None):
    global _WATCHERS
    if root_path in _WATCHERS:
        return
        
    stop_event = threading.Event()
    _WATCHERS[root_path] = stop_event
    
    def watch_thread():
        logger.info(f"Starting file watcher for {root_path}")
        try:
            for changes in watch(root_path, stop_event=stop_event):
                logger.info(f"Changes detected in {root_path}, re-indexing...")
                try:
                    index_project_impl(root_path, data_dir=data_dir, force_full=False, watch=False)
                except Exception as e:
                    logger.error(f"Error re-indexing project {root_path}: {e}")
        except Exception as e:
            logger.info(f"File watcher stopped for {root_path}: {e}")
        finally:
            _WATCHERS.pop(root_path, None)
            
    t = threading.Thread(target=watch_thread, daemon=True)
    t.start()

def index_project_impl(root_path: str, data_dir: str | None = None, force_full: bool = False, watch: bool = True) -> str:
    """Index the project and return db_id."""
    info = register_project(root_path, data_dir=data_dir)
    db_id = info["db_id"]
    
    root_p = Path(root_path)
    seen_file_ids = set()
    logger.info(f"indexing project: {root_path}")
    try:
        for rel_path, size, mtime, file_hash in scan_files(root_p):
            language = detect_language(rel_path)
            file_id, is_changed = insert_or_update_file(db_id, rel_path, language, file_hash, size, mtime, data_dir=data_dir)
            seen_file_ids.add(file_id)
            logger.debug(f"In loop detect language: {language}, is_changed: {is_changed},file_id: {file_id},rel_path: {rel_path}")
            logger.debug(f"Scanned file: {rel_path},language: {language},is_changed: {is_changed},file_id: {file_id}")
            
            if (is_changed or force_full) and language in ("python", "javascript", "typescript", "java", "csharp"):
                full_path = root_p / rel_path
                try:
                    with open(full_path, "rb") as f:
                        code_bytes = f.read()
                    logger.debug(f"Read file: {rel_path},language: {language},file_id: {file_id}")
                    # Symbols
                    symbols = extract_symbols(code_bytes, language)
                    logger.debug(f"Detect symbols: {symbols}")
                    insert_symbols(db_id, file_id, symbols, data_dir=data_dir)
                    
                    # Imports
                    imports = extract_imports(code_bytes, language)
                    if imports:
                        insert_imports(db_id, file_id, imports, data_dir=data_dir)
                        
                    # Calls
                    calls = extract_calls(code_bytes, language)
                    if calls:
                        insert_calls(db_id, file_id, calls, data_dir=data_dir)
                        
                    # Inheritance
                    inheritances = extract_inheritance(code_bytes, language)
                    if inheritances:
                        insert_inheritance(db_id, file_id, inheritances, data_dir=data_dir)
                        
                    # Framework routes
                    routes = []
                    if language == "python":
                        routes.extend(extract_django_routes(code_bytes, file_id))
                        routes.extend(extract_flask_routes(code_bytes, file_id))
                        routes.extend(extract_fastapi_routes(code_bytes, file_id))
                    elif language in ("javascript", "typescript"):
                        routes.extend(extract_react_routes(code_bytes, file_id))
                        routes.extend(extract_express_routes(code_bytes, file_id))
                        routes.extend(extract_nestjs_routes(code_bytes, file_id))
                        routes.extend(extract_vue_routes(code_bytes, file_id))
                        routes.extend(extract_angular_routes(code_bytes, file_id))
                    elif language == "java":
                        routes.extend(extract_spring_routes(code_bytes, file_id))
                    elif language == "csharp":
                        routes.extend(extract_dotnet_routes(code_bytes, file_id))
                        
                    if routes:
                        insert_routes(db_id, file_id, routes, data_dir=data_dir)
                    logger.debug(f"Extracted routes: {routes}")
                        
                except Exception as e:
                    logger.exception(f"Error extracting symbols/routes for {rel_path}: {e}")
        logger.info(f"Finished extracting symbols/routes for {root_path}")
                    
        # Cleanup deleted files
        from ucm_mcp.db.connection import get_connection
        conn = get_connection(db_id, data_dir)
        cur = conn.cursor()
        
        if seen_file_ids:
            placeholders = ",".join("?" for _ in seen_file_ids)
            cur.execute(f"DELETE FROM files WHERE id NOT IN ({placeholders})", list(seen_file_ids))
        else:
            cur.execute("DELETE FROM files")
        logger.info(f"Cleaned up files for {root_path}")
        conn.commit()
        
        # Update stats in registry
        from ucm_mcp.identity import update_project_stats
        cur.execute("SELECT COUNT(*) as c FROM files")
        total_files = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM symbols")
        total_symbols = cur.fetchone()["c"]
        update_project_stats(db_id, total_files, total_symbols, data_dir)
        
        logger.info(f"Finished cleanup for {root_path}")
        
        if watch:
            try:
                _start_watcher(root_path, db_id, data_dir)
                logger.info(f"Started file watcher for {root_path}")
            except Exception as e:
                logger.error(f"Error starting file watcher for {root_path}: {e}")

        logger.info(f"Finished indexing project: {root_path}")
        
        return db_id
    except Exception as e:
        logger.error(f"Error indexing project {root_path}: {e}")
        return str(e)
