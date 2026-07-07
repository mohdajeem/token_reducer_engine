# Engineering Documentation Index - Semantic Context Engine

This index provides a centralized navigation directory linking the complete, compiler-grade engineering documentation suite for the Semantic Context Engine.

---

## 📖 Complete Documentation Index

### 1. High-Level Core Philosophy & Architecture
*   **[Project Overview](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/PROJECT_OVERVIEW.md)**: Core mission, developer-to-AI agent lifecycle, and comparison details against Vector RAG and generic code review tools.
*   **[System Architecture](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/SYSTEM_ARCHITECTURE.md)**: Layered system map tracing parsers, match extractors, compilers, and BFS context/security engines.
*   **[Directory Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/DIRECTORY_GUIDE.md)**: Folder-by-folder layout guide mapping purposes, files, and dependency rules.

### 2. AST Extraction & Compilation Pipelines
*   **[Execution Flow](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/EXECUTION_FLOW.md)**: Detailed trace of `build_graph()` end-to-end (walking, parsing, SCM querying, matching, and building).
*   **[Tree-sitter Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/TREE_SITTER_GUIDE.md)**: AST queries, capture tags naming, classification rules, and route/call/DB extraction examples.
*   **[SemanticMatch Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/SEMANTIC_MATCH_GUIDE.md)**: Lifecycle, fields, and lexical function scopes of extracted `SemanticMatch` tokens.
*   **[GraphBuilder Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/GRAPH_BUILDER_GUIDE.md)**: Complete guide to GraphBuilder handlers (imports, definitions, routing, database, errors) and mutations.
*   **[Graph Schema Specification](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/GRAPH_SCHEMA.md)**: Full database dictionary structure, node definitions, and execution edge types (`FUNCTION_CALL`, `ROUTE_CALL`, `DB_ACCESS`).

### 3. Static Linkages, Data Flow, & Security Analyses
*   **[Symbol Table Linkage](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/SYMBOL_RESOLUTION.md)**: Inter-procedural linking, import resolutions, destructuring aliasing, and function mappings.
*   **[Data Flow Engine](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/DATA_FLOW_ENGINE.md)**: Positional parameter joins, variable assignments tracking, and return taint propagations.
*   **[Taint Analysis Security Engine](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/TAINT_ANALYSIS.md)**: Untrusted sources (`req.body`), query sinks (SQL/NoSQL Mongoose), sanitizers (`escape`), and findings.
*   **[Impact Analysis (Blast Radius)](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/IMPACT_ANALYSIS.md)**: Recursive BFS traversal algorithms calculating upstream caller dependencies and downstream dependents.

### 4. AI Payloads, Runtime, APIs, & Gaps
*   **[AI Context Engine](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/CONTEXT_ENGINE.md)**: Token-reduced snippet extraction, padding rules, and high-relevance JSON payload packaging.
*   **[Incremental Runtime Engine](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/INCREMENTAL_RUNTIME.md)**: Workspace snapshot hashes (`latest.json`), dirty node invalidators, and delta compilation rebuilds.
*   **[API reference Manual](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/API_REFERENCE.md)**: Python classes, CLI parameters, and Flask HTTP server endpoints specification.
*   **[Diagram Validation Report](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/DIAGRAM_VALIDATION_REPORT.md)**: Structured catalog and render checks for all Mermaid diagrams.

### 5. Contributor, Testing, & Maintenance Guides
*   **[Testing & Verification Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/TESTING_GUIDE.md)**: Test suite architecture, regression suites, and powershell encoding execution steps.
*   **[Static Analysis Debugging Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/DEBUGGING_GUIDE.md)**: Troubleshooting symptoms, causes, and trace logs for query, matching, and import issues.
*   **[Developer Extension Guide](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/DEVELOPMENT_GUIDE.md)**: Patterns for adding new language configurations, SCM queries, custom edges, or vulnerability passes.
*   **[Current Gaps & Limitations](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/CURRENT_LIMITATIONS.md)**: Honest review of dynamic imports, callback data mapping gaps, and scope name collision risks.
*   **[Future Roadmap Progressions](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/docs/FUTURE_ROADMAP.md)**: Development progression mapping low-latency watchers, deep type inference, and autonomous self-repair loops.
