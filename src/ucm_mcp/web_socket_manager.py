import time
from enum import Enum
from pydantic.main import BaseModel
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from typing import List, Union, Any
from abc import ABC
from ucm_mcp.logger import get_logger
import asyncio
logger = get_logger(__name__)

class WebSocketMessageType(Enum):
    NOTIFICATION = "notification"
    MESSAGE = "message"
    LOG = "log"
    PROGRESS = "progress"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    ERROR = "error"

class WebSocketMessageStatus(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class ToolName(Enum):
    UCM_INDEX_PROJECT = "ucm_index_project"
    UCM_SET_ACTIVE_PROJECT = "ucm_set_active_project"
    UCM_LIST_PROJECTS = "ucm_list_projects"
    UCM_PROJECT_OVERVIEW = "ucm_project_overview"
    UCM_DIRECTORY_MAP = "ucm_directory_map"
    UCM_FILE_MAP = "ucm_file_map"
    UCM_SEARCH = "ucm_search"
    UCM_FIND_CALLS = "ucm_find_calls"
    UCM_DEPENDENCIES = "ucm_dependencies"
    UCM_INHERITANCE = "ucm_inheritance"
    UCM_DEPENDENTS = "ucm_dependents"
    UCM_ROUTE_LOOKUP = "ucm_route_lookup"
    UCM_ARCHITECTURE_SUMMARY = "ucm_architecture_summary"
    UCM_IMPACT_ANALYSIS = "ucm_impact_analysis"
    UCM_DEAD_CODE_DETECTION = "ucm_dead_code_detection"
    UCM_DUPLICATE_DETECTION = "ucm_duplicate_detection"
    UCM_TEST_LOOKUP = "ucm_test_lookup"

class WebSocketMessage(BaseModel):
    type: WebSocketMessageType
    status: WebSocketMessageStatus
    content: str

class LiveMessage(WebSocketMessage):
    isError: bool
    timestamp: int

class ToolStartMessage(LiveMessage):
    toolName: str
    toolArgs: dict
    
    def __init__(self, **kwargs):
        kwargs["type"] = WebSocketMessageType.TOOL_START
        kwargs["status"] = WebSocketMessageStatus.INFO
        kwargs["isError"] = False
        super().__init__(**kwargs)

class ToolEndMessage(LiveMessage):
    toolName: str
    toolArgs: dict
    toolResult: Any
    
    def __init__(self, **kwargs):
        kwargs["type"] = WebSocketMessageType.TOOL_END
        kwargs["status"] = WebSocketMessageStatus.SUCCESS
        kwargs["isError"] = False
        super().__init__(**kwargs)


class WebSocketManager:
    def __init__(self):
        self.active_connections : list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        logger.info("WebSocket disconnected")
        await websocket.close()
        self.active_connections.remove(websocket)

    
    async def broadcast(self, message: WebSocketMessage):
        try:
            msg_json = message.model_dump(mode='json')
            logger.debug(f"Broadcasting message: {message.type} to {len(self.active_connections)} connections")
            for connection in self.active_connections:
                await connection.send_json(msg_json)
        except:
            logger.exception("Error broadcasting message")


web_socket_manager = WebSocketManager()


async def send_tool_start_Message(tool_name:str,tool_args:dict):
    try:
        await web_socket_manager.broadcast(ToolStartMessage(toolName=tool_name,toolArgs=tool_args,content=f"Starting tool {tool_name}",timestamp=int(time.time() * 1000)))
    except Exception as e:
        logger.exception("Error broadcasting message")

async def send_tool_end_Message(tool_name:str, tool_args:dict, tool_result:Any):
    try:
        await web_socket_manager.broadcast(ToolEndMessage(
            toolName=tool_name,
            toolArgs=tool_args,
            toolResult=tool_result,
            content=f"Finished tool {tool_name}",
            timestamp=int(time.time() * 1000)
        ))
    except Exception as e:
        logger.exception("Error broadcasting message")



    