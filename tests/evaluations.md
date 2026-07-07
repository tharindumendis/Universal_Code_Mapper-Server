# UCM MCP Server - Evaluations

This document contains 10 realistic read-only Q&A pairs that an AI agent might use to verify the usefulness of the Universal Code Mapper (UCM) MCP Server against a codebase. 

## Scenarios

**1. Finding where a specific service is used**
- **User:** "Find all places where the `calculate_profit` function is called."
- **Agent Action:** `ucm_find_callers(symbol_name="calculate_profit")`
- **Result:** Returns a list of caller functions across multiple files, enabling the agent to analyze the impact of modifying `calculate_profit`.

**2. Discovering Database Models**
- **User:** "What database models exist in this Django project?"
- **Agent Action:** `ucm_search_keywords(terms=["models.Model", "models"])` or `ucm_architecture_summary()`
- **Result:** The agent retrieves a breakdown of the architecture, identifying all files mapped to "Models/Entities", then can map those specific files via `ucm_file_map`.

**3. Tracing Route Handlers**
- **User:** "Where is the handler for `POST /api/users`?"
- **Agent Action:** `ucm_route_lookup(method="POST", path="/api/users")`
- **Result:** The tool directly returns the handler symbol name (e.g., `create_user_view`) and its filepath, skipping manual grep.

**4. Assessing Code Impact**
- **User:** "If I change `AuthService`, what parts of the system are affected?"
- **Agent Action:** `ucm_impact_analysis(symbol_name="AuthService", depth=3)`
- **Result:** Returns all transitive callers, endpoints, and tests that depend on `AuthService`, providing a complete blast radius.

**5. Exploring Class Inheritance**
- **User:** "What classes inherit from `BasePlugin`?"
- **Agent Action:** `ucm_inheritance(symbol_name="BasePlugin")`
- **Result:** Returns all child classes and their filepaths, revealing plugin implementations across the repo.

**6. Cleaning Up Dead Code**
- **User:** "Are there any unused functions we can safely delete?"
- **Agent Action:** `ucm_dead_code_detection(symbol_types=["function", "method"])`
- **Result:** Identifies unreferenced symbols. The agent can then cross-reference with route lookups to ensure they are truly dead.

**7. Investigating Dependency Chains**
- **User:** "What modules does `payment_gateway.py` rely on?"
- **Agent Action:** `ucm_dependencies(file_path="payment_gateway.py")`
- **Result:** Lists all explicit and dynamic imports within the file, mapping out its dependencies.

**8. Finding tests for a symbol**
- **User:** "Does the `process_order` function have any test coverage?"
- **Agent Action:** `ucm_test_lookup(symbol_name="process_order")`
- **Result:** Returns a list of tests containing `process_order` in their name or test files calling `process_order`.

**9. Analyzing Project Layout**
- **User:** "How is the `/src/services` directory structured?"
- **Agent Action:** `ucm_directory_map(dir_path="/src/services", depth=2)`
- **Result:** Provides a structural map of classes and functions contained within the directory without exposing the full raw code.

**10. General Keyword Search**
- **User:** "Find any code related to 'JWT authentication' or 'token expiry'."
- **Agent Action:** `ucm_search_keywords(terms=["JWT", "token", "expiry", "authentication"])`
- **Result:** Leverages SQLite FTS5 BM25 search over symbols and docstrings to find highly relevant areas of code, avoiding embeddings dependencies.
