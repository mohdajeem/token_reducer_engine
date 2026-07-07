# Directory Guide - Semantic Context Engine

This document outlines the folder layout of the Semantic Context Engine repository. It details the purpose, direct compiler responsibilities, important files, and internal dependency limits of each folder.

---

## Workspace Directory Map

The streamlined `src/` directory contains only clean, active modules. All legacy duplications and placeholder folders are safely isolated under `archive/`.

```
token_reducer_system/
├── archive/                   # Isolated Duplicate, Legacy & Abandoned Modules
│   ├── abandoned/             # Empty placeholder directories & Commented out pipelines
│   ├── duplicate_versions/    # Duplicate semantic packages & Obsolete test runners
│   └── legacy/                # Retired model review controllers & LLM connectors
├── docs/                      # Engineering Documentation (Mermaid-rich guides)
├── test_microservice/         # Real microservice project used for integration validation
├── src/                       # Active Core System Directory
│   ├── api/                   # Flask HTTP Integration Server
│   ├── config/                # Global Settings & Debug Configuration Constants
│   ├── context_engine/        # Context Extraction Payloads
│   ├── impact_engine/         # BFS Graph Traversals & Taint propagation
│   ├── incremental_runtime/   # Snapshots, Invalidators & WATCHERS
│   ├── queries/               # Tree-sitter SCM Master Query specifications
│   ├── semantic_core/         # AST Matching & Graph Compiler
│   ├── tests/                 # Dedicated regression tests & master suite
│   ├── utils/                 # Logging Wrappers
│   └── validation/            # Patch simulators & semantic rule validations
```

---

## Detailed Directory Catalog

### 1. `src/semantic_core/`
*   **Purpose**: Houses the core AST semantic matching, classification, and symbol linking machinery.
*   **Key Responsibilities**:
    *   Walk project directories and parse files into ASTs using tree-sitter.
    *   Extract and classify raw captures into `SemanticMatch` blocks.
    *   Maintain symbols, aliases, destructuring patterns, and function indexes.
    *   Compile raw matches into execution graphs and data flows.
*   **Important Files**:
    *   [graph_builder.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/graph_builder.py) - Central compiler entry point.
    *   [match_extractor_fixed.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_extractor_fixed.py) - Safe AST query extractor with range caching.
    *   [symbol_table.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/symbol_table.py) - Handles linkages and symbol scope aliasing.
*   **Dependencies**: `src/queries/`, `tree_sitter`, `src/config/`.

### 2. `src/impact_engine/`
*   **Purpose**: The central static analysis, dependency tracking, and taint tracking engine.
*   **Key Responsibilities**:
    *   Trace dependency chains forward (dependent routes/sinks) and backward (upstream callers).
    *   Track the propagation of untrusted user input along inter-procedural data flows.
    *   Identify un-sanitized routes mapping to database sinks (SQL injection, NoSQL injection).
*   **Important Files**:
    *   [taint_traversal_engine.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/taint_traversal_engine.py) - Propagates taint across variables and calls.
    *   [graph_traversal.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/graph_traversal.py) - BFS orchestrator tracing edge matches.
*   **Dependencies**: Depends strictly on compiled graph objects from `src/semantic_core/`.

### 3. `src/context_engine/`
*   **Purpose**: Packaging minimized semantic context payloads for AI agents.
*   **Key Responsibilities**:
    *   Compute change impact blast radius.
    *   Retrieve high-relevance code spans and snippets surrounding impacted functions.
    *   Filter out generic noise and output compressed context JSON.
*   **Important Files**:
    *   [context_extractor.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/context_engine/context_extractor.py) - Traverses blast radius and packages snippet strings.
*   **Dependencies**: `src/impact_engine/graph_traversal.py`, `src/language_config.py`.

### 4. `src/validation/`
*   **Purpose**: Verifies semantic patch safety and correctness.
*   **Key Responsibilities**:
    *   Analyze unresolved symbols or reference breakages virtually.
    *   Simulate code diff patches on the AST and assert syntax validity.
    *   Audit patch changes for newly introduced dangerous imports or untrusted APIs.
*   **Important Files**:
    *   [semantic_validator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/semantic_validator.py) - Asserts graph safety constraints.
    *   [patch_validator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_validator.py) - Simulates git diff patches and analyzes AST errors.
*   **Dependencies**: `src/impact_engine/`, `src/semantic_core/`.

### 5. `src/incremental_runtime/`
*   **Purpose**: Optimizes compilation through file watching and delta rebuilds.
*   **Key Responsibilities**:
    *   Track file modification timestamps.
    *   Compare AST snapshot invalidations to determine dirty nodes.
    *   Selectively re-compile only modified file branches in the graph.
*   **Important Files**:
    *   [incremental_graph_manager.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/incremental_graph_manager.py) - Coordinates changes.
    *   [graph_invalidator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/graph_invalidator.py) - Marks dirty node dependencies.
*   **Dependencies**: `src/semantic_core/`, `src/impact_engine/`.
