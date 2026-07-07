from fastmcp import FastMCP
from ucm_mcp.tools.project_tools import register_project_tools
from ucm_mcp.tools.overview_tools import register_overview_tools
from ucm_mcp.tools.search_tools import register_search_tools

def build_server(data_dir: str | None = None) -> FastMCP:
    """
    Build and return the FastMCP server instance for Universal Code Mapper.
    """
    mcp = FastMCP("ucm_mcp")
    
    register_project_tools(mcp, data_dir=data_dir)
    register_overview_tools(mcp, data_dir=data_dir)
    register_search_tools(mcp, data_dir=data_dir)
    from ucm_mcp.tools.graph_tools import register_graph_tools
    register_graph_tools(mcp, data_dir)
    from ucm_mcp.tools.framework_tools import register_framework_tools
    register_framework_tools(mcp, data_dir)
    from ucm_mcp.tools.analysis_tools import register_analysis_tools
    register_analysis_tools(mcp, data_dir)
    from ucm_mcp.tools.test_tools import register_test_tools
    register_test_tools(mcp, data_dir)
    
    return mcp
