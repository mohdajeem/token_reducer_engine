# Dependency Map - Semantic Context Engine

This document provides the complete, traced dependency mapping of the active Semantic Context Engine modules. It outlines **Consumers** (who imports a file) and **Dependencies** (what a file imports) to guarantee zero linkage breakages during our forensic cleanup.

---

## 1. CLI & Server Entrypoints

### `src/main.py`
*   **Consumers**: None (Standalone command-line entrypoint)
*   **Dependencies**:
    *   [settings.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/config/settings.py)
    *   [graph_builder.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/graph_builder.py)
    *   [graph_traversal.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/graph_traversal.py)
    *   [taint_traversal_engine.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/taint_traversal_engine.py)
    *   [context_extractor.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/context_engine/context_extractor.py)
    *   [change_detector.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/change_detector.py)
    *   [graph_invalidator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/graph_invalidator.py)
    *   [semantic_validator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/semantic_validator.py)
    *   [patch_validator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_validator.py)

### `src/build_graph.py`
*   **Consumers**: None (Standalone orchestrator)
*   **Dependencies**:
    *   [logger.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/utils/logger.py)
    *   [language_config.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/language_config.py)
    *   [graph_builder.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/graph_builder.py)
    *   [match_extractor_fixed.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_extractor_fixed.py)
    *   [taint_traversal_engine.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/taint_traversal_engine.py)
    *   [settings.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/config/settings.py)

### `src/api/server.py`
*   **Consumers**: None (Runs the AI context HTTP integration server)
*   **Dependencies**:
    *   [settings.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/config/settings.py)
    *   [graph_builder.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/graph_builder.py)
    *   [graph_traversal.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/graph_traversal.py)
    *   [context_extractor.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/context_engine/context_extractor.py)
    *   [change_detector.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/change_detector.py)
    *   [semantic_validator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/semantic_validator.py)
    *   [patch_validator.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_validator.py)

---

## 2. Core Parser & Semantic Engine Components

### `src/language_config.py`
*   **Consumers**:
    *   `src/build_graph.py`
    *   `src/test_runner_proper.py`
    *   `src/semantic_core/match_extractor_fixed.py`
    *   `src/incremental_runtime/change_detector.py`
    *   `src/validation/patch_semantic_extractor.py`
    *   `src/validation/patch_validator.py`
*   **Dependencies**: None

### `src/semantic_core/graph_builder.py`
*   **Consumers**:
    *   `src/main.py`, `src/build_graph.py`, `src/api/server.py`, `src/test_runner_proper.py`, `src/quick_test.py`
    *   All test suites in `src/tests/`
*   **Dependencies**:
    *   [symbol_table.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/symbol_table.py)
    *   [function_index.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/function_index.py)
    *   [express_route_normalizer.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/frameworks/express_route_normalizer.py)
    *   [settings.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/config/settings.py)

### `src/semantic_core/match_extractor_fixed.py`
*   **Consumers**:
    *   `src/build_graph.py`, `src/test_runner_proper.py`, `src/incremental_runtime/change_detector.py`
    *   All test suites in `src/tests/`
*   **Dependencies**:
    *   [language_config.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/language_config.py)
    *   [semantic_match.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/semantic_match.py)
    *   [match_classifier.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_classifier.py)

### `src/semantic_core/match_classifier.py`
*   **Consumers**:
    *   `src/semantic_core/match_extractor_fixed.py`
*   **Dependencies**: None

---

## 3. Impact & Taint Traversal Components

### `src/impact_engine/taint_traversal_engine.py`
*   **Consumers**:
    *   `src/main.py`, `src/build_graph.py`
*   **Dependencies**: None

### `src/impact_engine/graph_traversal.py`
*   **Consumers**:
    *   `src/main.py`, `src/api/server.py`, `src/test_runner_proper.py`, `src/quick_test.py`
    *   `src/impact_engine/taint_traversal_engine.py`
    *   `src/impact_engine/impact_analysis.py`
    *   `src/impact_engine/function_query.py`
    *   `src/impact_engine/symbol_query.py`
    *   `src/context_engine/context_extractor.py`
*   **Dependencies**: None

---

## 4. AI Context Extraction Components

### `src/context_engine/context_extractor.py`
*   **Consumers**:
    *   `src/main.py`, `src/api/server.py`, `src/test_runner_proper.py`, `src/quick_test.py`
    *   All end-to-end integration tests
*   **Dependencies**:
    *   [graph_traversal.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/graph_traversal.py)
    *   [language_config.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/language_config.py)

---

## 5. Incremental Compilation Components

### `src/incremental_runtime/change_detector.py`
*   **Consumers**:
    *   `src/main.py`, `src/api/server.py`
    *   `src/incremental_runtime/incremental_graph_manager.py`
*   **Dependencies**:
    *   [language_config.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/language_config.py)
    *   [match_extractor_fixed.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_extractor_fixed.py)

### `src/incremental_runtime/graph_invalidator.py`
*   **Consumers**:
    *   `src/main.py`
    *   `src/incremental_runtime/incremental_graph_manager.py`
*   **Dependencies**: None

---

## 6. Semantic Validation Components

### `src/validation/semantic_validator.py`
*   **Consumers**:
    *   `src/main.py`, `src/api/server.py`, `src/test_runner_proper.py`, `src/quick_test.py`
    *   `src/validation/__init__.py`
*   **Dependencies**:
    *   [patch_semantic_extractor.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_semantic_extractor.py)
    *   [trusted_symbol_registry.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/trusted_symbol_registry.py)
    *   [function_query.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/function_query.py)
    *   [symbol_query.py](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/symbol_query.py)
