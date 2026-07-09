import logging
import sys
import os
from ucm_mcp.config import get_base_dir

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Use stderr so we don't corrupt MCP's stdout json-rpc stream
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Add FileHandler
        try:
            base_dir = get_base_dir(os.environ.get("UCM_DATA_DIR"))
            log_dir = base_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "ucm-mcp.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging: {e}", file=sys.stderr)

        # Prevent log messages from being propagated to the root logger
        logger.propagate = False
    return logger
