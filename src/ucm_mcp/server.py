from fastapi import FastAPI
from fastmcp import FastMCP
from ucm_mcp.tools.project_tools import register_project_tools
from ucm_mcp.tools.overview_tools import register_overview_tools
from ucm_mcp.tools.search_tools import register_search_tools

def build_server(data_dir: str | None = None, mcp:FastMCP | None = None, app: FastAPI | None = None) -> FastMCP:
    """
    Build and return the FastMCP server instance for Universal Code Mapper.
    """
    # mcp = FastMCP("ucm_mcp")

    project_router = register_project_tools(mcp, data_dir=data_dir)
    overview_router = register_overview_tools(mcp, data_dir=data_dir)
    search_router = register_search_tools(mcp, data_dir=data_dir)
    from ucm_mcp.tools.graph_tools import register_graph_tools
    graph_router = register_graph_tools(mcp, data_dir)
    from ucm_mcp.tools.framework_tools import register_framework_tools
    framework_router = register_framework_tools(mcp, data_dir)
    from ucm_mcp.tools.analysis_tools import register_analysis_tools
    analysis_router = register_analysis_tools(mcp, data_dir)
    from ucm_mcp.tools.test_tools import register_test_tools
    test_router = register_test_tools(mcp, data_dir)

    app.include_router(project_router)
    app.include_router(overview_router)
    app.include_router(search_router)
    app.include_router(graph_router)
    app.include_router(framework_router)
    app.include_router(analysis_router)
    app.include_router(test_router)
    
    
    return mcp, app
