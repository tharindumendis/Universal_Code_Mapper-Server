# Universal Code Mapper (UCM) MCP Server

UCM is a fast, offline, Universal Code Mapper exposed as a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server. It enables AI coding assistants (like Claude) to navigate, search, and understand your codebases structurally without relying on embeddings or cloud AI dependencies.

## ✨ Features

- **Blazing Fast**: Uses `tree-sitter` for rapid parsing and SQLite FTS5 for full-text search. No embeddings!
- **Interactive Web UI**: Comes with a built-in network graph visualization to explore your codebase map in the browser.
- **Call Graphs & Relationships**: Traverse callers, callees, inheritance, and dependencies.
- **Framework Aware**: Extensively extracts routes and architectural heuristics for Django and React.
- **Incremental Indexing**: Instant re-indexing of unchanged files using `mtime` and content hashing.
- **Agent-Optimized Tools**: Designed specifically for LLMs to easily understand project architecture, route maps, and dead code.

---

## 📦 Installation

UCM can be installed directly from PyPI. We recommend using [`uv`](https://github.com/astral-sh/uv) for the fastest installation and execution:

```bash
uv tool install ucm-mcp
```

Or using standard `pip`:

```bash
pip install ucm-mcp
```

---

## 🚀 Quickstart

### 1. The Interactive Web UI

UCM comes with a rich, interactive web UI to visualize your codebase architecture, view full network graphs, and run architectural analysis. 

When you run UCM, the visualizer UI is automatically served in the background!

```bash
uvx ucm-mcp
# Or if installed globally:
# ucm-mcp
```

Upon startup, you will see a banner in your terminal:
```text
============================================================
🚀 UCM Backend is running!
🌐 Open the UI at: https://ucm-ui.netlify.app/?port=8000
============================================================
```
Click the link to open the Visualizer UI, which will automatically connect to your local backend.

### 2. Setting up in Claude Desktop (MCP Client)

To give Claude (or any other MCP-compatible AI assistant) access to your codebase architecture, add UCM to your MCP client configuration.

**For Claude Desktop (`claude_desktop_config.json`):**

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

*Note: Even when running inside Claude, the background Web UI will still be active and available to you via the browser!*

---

## 🛠️ Usage & Tools

Once connected, your AI assistant will have access to a powerful suite of tools to understand your code. 

**First Step:**
- `ucm_index_project`: Indexes the specified directory. This **must** be called before queries work. (The UI can also trigger this index!)

**Exploration Tools:**
- `ucm_search_symbol` / `ucm_search_keywords`: Powerful search over AST symbols and full-text code.
- `ucm_file_map` / `ucm_directory_map`: View the hierarchical layout of the project.
- `ucm_get_symbol_info`: Retrieve detailed AST information about a specific class, function, or method.

**Analysis Tools:**
- `ucm_find_callers` / `ucm_find_callees`: Trace execution paths and function calls.
- `ucm_impact_analysis`: Check what breaks when a specific function or class is modified.
- `ucm_architecture_summary`: Automatically generates a high-level overview of the project structure.
- `ucm_route_lookup`: Automatically extracts web framework routes (e.g., Django, React).
- `ucm_dead_code_detection`: Identifies unused functions and classes.

---

## ⚙️ Advanced Configuration

You can customize the UCM server using the following CLI arguments:

- `--port <PORT>`: Change the default port (8000) for the UI server.
- `--http`: Run exclusively in HTTP (SSE) mode instead of standard MCP stdio.
- `--data-dir <PATH>`: Override the default SQLite storage location (defaults to `~/.ucm`).
