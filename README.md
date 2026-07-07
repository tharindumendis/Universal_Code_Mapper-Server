# Universal Code Mapper (UCM) MCP Server

UCM is a fast, offline, Universal Code Mapper exposed as a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server. It enables AI coding assistants (like Claude) to navigate, search, and understand your codebases structurally without relying on embeddings or cloud AI dependencies.

## Features

- **Blazing Fast**: Uses `tree-sitter` for rapid parsing and SQLite FTS5 for full-text search. No embeddings!
- **Call Graphs & Relationships**: Traverse `ucm_find_callers`, `ucm_find_callees`, `ucm_inheritance`, and `ucm_dependencies`.
- **Framework Aware**: Extensively extracts routes and architectural heuristics for Django and React.
- **Incremental Indexing**: Instant re-indexing of unchanged files using `mtime` and content hashing.
- **Agent-Optimized Tools**: Designed specifically for LLMs to easily understand the project architecture (`ucm_architecture_summary`), route maps (`ucm_route_lookup`), and dead code (`ucm_dead_code_detection`).

## Setup in Claude Desktop or other MCP Clients

You can run UCM directly via `uvx` (the ultra-fast `uv` tool runner). Zero installation required!

In your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ucm": {
      "command": "uvx",
      "args": [
        "ucm-mcp"
      ]
    }
  }
}
```

If you prefer streamable HTTP mode:

```json
{
  "mcpServers": {
    "ucm": {
      "command": "uvx",
      "args": [
        "ucm-mcp",
        "--http",
        "--port",
        "8000"
      ]
    }
  }
}
```

## How to use

Once connected, your AI assistant will have access to the following key tools:
- `ucm_index_project`: Indexes the specified directory. This **must** be called before queries work.
- `ucm_search_symbol` / `ucm_search_keywords`: Powerful search over AST symbols.
- `ucm_file_map` / `ucm_directory_map`: View the layout of the project.
- `ucm_impact_analysis`: Check what breaks when a function is changed.
