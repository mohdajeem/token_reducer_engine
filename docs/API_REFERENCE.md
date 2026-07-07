# API Reference - Semantic Context Engine

This document provides the complete API specification for the Semantic Context Engine, including Python class interfaces, command-line arguments, and Flask HTTP server endpoints.

---

## 1. Python Class References

### A. `GraphBuilder` (`src/semantic_core/graph_builder.py`)
Central compiler class for assembling the semantic graph from extracted matches.
*   **`__init__(self)`**: Initializes symbol tables, normalizers, and empty graph dictionaries.
*   **`build(self, semantic_matches: List[SemanticMatch]) -> Dict`**:
    *   **Description**: Ingests list of matches, runs compiler passes, resolves scopes, compiles execution edges, maps parameter/argument flows, and performs taint analysis.
    *   **Returns**: The completed Semantic Graph dictionary object (see [Graph Schema Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/GRAPH_SCHEMA.md)).

### B. `GraphTraversal` (`src/impact_engine/graph_traversal.py`)
Orchestrates BFS searches across the execution graph edges.
*   **`find_upstream_nodes(self, target_node: Dict) -> List[Dict]`**:
    *   **Parameters**: `target_node` (e.g. `{"type": "FUNCTION", "file": "userService.js", "function": "fetchUsers"}`).
    *   **Returns**: List of trace edge dictionaries representing upstream callers.
*   **`find_downstream_nodes(self, target_node: Dict) -> List[Dict]`**:
    *   **Returns**: List of trace edge dictionaries representing downstream dependents.

### C. `ContextExtractor` (`src/context_engine/context_extractor.py`)
Extracts padded code snippets and packs AI context.
*   **`extract_context(self, impact: Dict) -> Dict`**:
    *   **Parameters**: `impact` dictionary containing `target`, `upstream`, and `downstream` lists.
    *   **Returns**: Minimized AI Context payload dictionary (containing `relevant_files`, `relevant_functions`, `code_snippets`).

---

## 2. Command-Line Interface (CLI)

The CLI tool can be executed via `src/main.py`:
```bash
python -m main [options] [target_directory]
```

### Options
*   `target_directory` (positional): The absolute or relative path of the project directory to parse (defaults to `../test_microservice`).
*   `--debug`: Enables detailed logger outputs showing parsing details and match extractions.

---

## 3. Flask HTTP Server API (`src/api/server.py`)

The Flask server provides low-latency HTTP endpoints for real-time tool integration (e.g., IDE plugins or review pipelines).
*   **Default Port**: `5000`
*   **Start Command**: `python -m api.server`

### A. `GET /health`
*   **Description**: Returns server operational status.
*   **Response**: `{"status": "ok"}`

### B. `POST /api/build`
*   **Description**: Builds the semantic graph for the target workspace.
*   **Payload**: `{"directory": "C:/app/test_microservice"}`
*   **Response**:
    ```json
    {
      "status": "success",
      "files_parsed": 4,
      "matches_found": 83,
      "graph_summary": {
        "imports": 5,
        "routes": 13,
        "calls": 7,
        "database": 3,
        "execution_edges": 33,
        "functions": 3
      }
    }
    ```

### C. `POST /api/impact`
*   **Description**: Computes blast radius around a changed function.
*   **Payload**:
    ```json
    {
      "function_name": "getAllUsers",
      "file_path": "controllers/userController.js"
    }
    ```
*   **Response**:
    ```json
    {
      "status": "success",
      "impact": {
        "target": "getAllUsers",
        "upstream": 0,
        "downstream": 1
      }
    }
    ```

### D. `POST /api/context`
*   **Description**: Generates the complete token-reduced AI context payload for the blast radius.
*   **Payload**: Same as `/api/impact` payload.
*   **Response**: Returns the [Context Extractor Payload](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/CONTEXT_ENGINE.md).
