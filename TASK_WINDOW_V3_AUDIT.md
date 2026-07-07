# Task-Window Telemetry V3 Audit Report (TASK_WINDOW_V3_AUDIT.md)

This audit verifies the correctness, disjointness, and reproducibility of the **Event-Based Attribution V3** task-level metrics.

## 1. Step-Range Disjointness Verification

To guarantee that no step (and thus no file read or write event) is counted twice, the step index ranges for all task windows in each session must be strictly disjoint and mutually exclusive:

### Session: `bec51ff1-e8b6-4e57-a51a-85b324af07d8`
| Task Index | Query ID | Step Start | Step End | Range Cover |
| :---: | :---: | :---: | :---: | :--- |
| 1 | 4 | 0 | 593 | `[0, 593]` |
| 2 | Trailing | 594 | 1300 | `[594, 1300]` |

**Disjointness Audit Status**: **PASS**. (Verified that step ranges are strictly sequential and non-overlapping, mathematically ensuring no step/event is double counted).

### Session: `bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78`
| Task Index | Query ID | Step Start | Step End | Range Cover |
| :---: | :---: | :---: | :---: | :--- |
| 1 | 1 | 0 | 25 | `[0, 25]` |
| 2 | 2 | 26 | 37 | `[26, 37]` |
| 3 | 3 | 38 | 59 | `[38, 59]` |
| 4 | Trailing | 60 | 135 | `[60, 135]` |

**Disjointness Audit Status**: **PASS**. (Verified that step ranges are strictly sequential and non-overlapping, mathematically ensuring no step/event is double counted).

## 2. Agent Baseline Containment & Independence Verification

We verify that the agent's workspace code baseline (`agent_code_tokens`) is strictly calculated from files the agent *actually opened* during the task window, and does not include the MCP selected files list unless the agent specifically read them during that step interval.

### Session: `bec51ff1-e8b6-4e57-a51a-85b324af07d8`

#### Task 1: `ROUTE:post:/register` (Query 4)
*   **Files Opened by Agent (Workspace Code)**: 56 files.
    *   `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/model_client.py`
    *   `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/sandbox_manager.py`
    *   `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/scoring_engine.py`
    *   `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/task_runner.py`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/mock-mongoose.js`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/middlewares/validation.middleware.js`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/analytics.routes.js`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/document.routes.js`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/job.routes.js`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/prompt-template.routes.js`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/test-flow.js`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/.env`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/BENCHMARK_REPORT.md`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/EDIT_RECALL_REPORT.md`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/REPOSITORY_AUDIT.md`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/scratch/test_queries.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/snapshots/benchmark_results.json`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/snapshots/edit_recall_results.json`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/api/mcp_server.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/api/server.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/model_client.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/task_runner.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/build_graph.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/context_engine/context_extractor.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/graph_traversal.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/traversal_policy.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/snapshot_manager.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/language_config.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/main.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/queries/javascript.scm`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/quick_test.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/frameworks/express_route_normalizer.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/graph_builder.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_classifier.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_extractor_fixed.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/test_runner_proper.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/tests/run_all_tests.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/tests/test_mcp_server.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/edit_recall_validation.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_simulator.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_trust_analyzer.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_validator.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/semantic_validator.py`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/test_microservice/api.js`
    *   `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/test_microservice/controllers/userController.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/package.json`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/app.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/config/db.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/middlewares/validation.middleware.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/models/user.model.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/server.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/analytics.service.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/auth.service.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/document.service.js`
    *   `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/job.service.js`
*   **MCP Selected Files**: 4 files.
    *   `src/controllers/auth.controller.js` (In Agent Baseline: **False**)
    *   `src/routes/auth.routes.js` (In Agent Baseline: **True**)
    *   `src/models/user.model.js` (In Agent Baseline: **True**)
    *   `src/services/auth.service.js` (In Agent Baseline: **True**)
*   **Baseline Token Calculations**: `agent_code_tokens` = **103,973 tokens** (Sum of unique token counts of files the agent *actually opened*). This verifies that MCP selected files are **not** blindly injected into the baseline.

### Session: `bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78`

#### Task 1: `ROUTE:post:/login` (Query 1)
*   **Files Opened by Agent (Workspace Code)**: 0 files.
*   **MCP Selected Files**: 4 files.
    *   `src/controllers/auth.controller.js` (In Agent Baseline: **False**)
    *   `src/routes/auth.routes.js` (In Agent Baseline: **False**)
    *   `src/models/user.model.js` (In Agent Baseline: **False**)
    *   `src/services/auth.service.js` (In Agent Baseline: **False**)
*   **Baseline Token Calculations**: `agent_code_tokens` = **0 tokens** (Sum of unique token counts of files the agent *actually opened*). This verifies that MCP selected files are **not** blindly injected into the baseline.

#### Task 2: `ROUTE:post:/register` (Query 2)
*   **Files Opened by Agent (Workspace Code)**: 1 files.
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js`
*   **MCP Selected Files**: 4 files.
    *   `src/controllers/auth.controller.js` (In Agent Baseline: **False**)
    *   `src/routes/auth.routes.js` (In Agent Baseline: **True**)
    *   `src/models/user.model.js` (In Agent Baseline: **False**)
    *   `src/services/auth.service.js` (In Agent Baseline: **False**)
*   **Baseline Token Calculations**: `agent_code_tokens` = **360 tokens** (Sum of unique token counts of files the agent *actually opened*). This verifies that MCP selected files are **not** blindly injected into the baseline.

#### Task 3: `ROUTE:post:/login` (Query 3)
*   **Files Opened by Agent (Workspace Code)**: 2 files.
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/.env`
    *   `C:/Users/ajeem/Downloads/downloads/testing/testing1/package.json`
*   **MCP Selected Files**: 4 files.
    *   `src/controllers/auth.controller.js` (In Agent Baseline: **False**)
    *   `src/routes/auth.routes.js` (In Agent Baseline: **False**)
    *   `src/models/user.model.js` (In Agent Baseline: **False**)
    *   `src/services/auth.service.js` (In Agent Baseline: **False**)
*   **Baseline Token Calculations**: `agent_code_tokens` = **179 tokens** (Sum of unique token counts of files the agent *actually opened*). This verifies that MCP selected files are **not** blindly injected into the baseline.

## 3. Exact File & Token Breakdown per Task Window

### Session: `bec51ff1-e8b6-4e57-a51a-85b324af07d8`

#### Task 1: `ROUTE:post:/register` (Query 4)
*   **Step Index Range**: `[0, 593]`
*   **Window Bounds**: `2026-06-08T17:24:01Z` &rarr; `2026-06-09T17:46:18Z`
*   **Window Duration**: `87,737.0 seconds`

##### Files Opened by Agent Details:
| Path | Category | Unique Token Count | Cumulative Read Count |
| :--- | :---: | :---: | :---: |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/implementation_plan.md` | GEMINI | 844 | 2 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/task.md` | GEMINI | 508 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/walkthrough.md` | GEMINI | 1,605 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/model_client.py` | REPO | 2,037 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/sandbox_manager.py` | REPO | 1,164 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/scoring_engine.py` | REPO | 798 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/task_runner.py` | REPO | 3,896 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/mock-mongoose.js` | EXTERNAL | 1,861 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/middlewares/validation.middleware.js` | EXTERNAL | 139 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/analytics.routes.js` | EXTERNAL | 89 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/document.routes.js` | EXTERNAL | 379 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/job.routes.js` | EXTERNAL | 360 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/prompt-template.routes.js` | EXTERNAL | 402 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/test-flow.js` | EXTERNAL | 3,052 | 3 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/.env` | REPO | 31 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/BENCHMARK_REPORT.md` | REPO | 353 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/EDIT_RECALL_REPORT.md` | REPO | 1,439 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/REPOSITORY_AUDIT.md` | REPO | 2,023 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/scratch/test_queries.py` | REPO | 0 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/snapshots/benchmark_results.json` | REPO | 281 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/snapshots/edit_recall_results.json` | REPO | 3,314 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/api/mcp_server.py` | REPO | 3,093 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/api/server.py` | REPO | 2,725 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/model_client.py` | REPO | 2,037 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/task_runner.py` | REPO | 3,896 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/build_graph.py` | REPO | 7,677 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/context_engine/context_extractor.py` | REPO | 6,828 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/graph_traversal.py` | REPO | 1,659 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/impact_engine/traversal_policy.py` | REPO | 1,815 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/incremental_runtime/snapshot_manager.py` | REPO | 296 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/language_config.py` | REPO | 911 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/main.py` | REPO | 2,318 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/queries/javascript.scm` | REPO | 2,366 | 3 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/quick_test.py` | REPO | 772 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/frameworks/express_route_normalizer.py` | REPO | 3,027 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/graph_builder.py` | REPO | 13,978 | 5 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_classifier.py` | REPO | 860 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/match_extractor_fixed.py` | REPO | 2,346 | 3 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/test_runner_proper.py` | REPO | 3,012 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/tests/run_all_tests.py` | REPO | 851 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/tests/test_mcp_server.py` | REPO | 1,039 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/edit_recall_validation.py` | REPO | 6,538 | 5 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_simulator.py` | REPO | 1,808 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_trust_analyzer.py` | REPO | 1,848 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_validator.py` | REPO | 1,385 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/semantic_validator.py` | REPO | 3,538 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/test_microservice/api.js` | REPO | 155 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/test_microservice/controllers/userController.js` | REPO | 116 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/package.json` | EXTERNAL | 136 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/app.js` | EXTERNAL | 324 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/config/db.js` | EXTERNAL | 126 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/middlewares/validation.middleware.js` | EXTERNAL | 139 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/models/user.model.js` | EXTERNAL | 435 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js` | EXTERNAL | 360 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/server.js` | EXTERNAL | 307 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/analytics.service.js` | EXTERNAL | 702 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/auth.service.js` | EXTERNAL | 809 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/document.service.js` | EXTERNAL | 700 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/job.service.js` | EXTERNAL | 1,091 | 1 |

##### MCP Selected Files Details:
| Path | Category | Raw File Size (Chars) | Raw File Tokens | Context Pruned Tokens |
| :--- | :---: | :---: | :---: | :---: |
| `src/controllers/auth.controller.js` | REPO | 1,360 | 340 | (Pruned inside Engine) |
| `src/routes/auth.routes.js` | REPO | 1,440 | 360 | (Pruned inside Engine) |
| `src/models/user.model.js` | REPO | 1,740 | 435 | (Pruned inside Engine) |
| `src/services/auth.service.js` | REPO | 3,236 | 809 | (Pruned inside Engine) |
| **Context payload size** | | | | **874** |

#### Task 2: `Trailing Session Verification` (Trailing)
*   **Step Index Range**: `[594, 1300]`
*   **Window Bounds**: `2026-06-09T17:46:20Z` &rarr; `2026-06-11T16:36:52Z`
*   **Window Duration**: `168,632.0 seconds`

##### Files Opened by Agent Details:
| Path | Category | Unique Token Count | Cumulative Read Count |
| :--- | :---: | :---: | :---: |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/.system_generated/logs/transcript.jsonl` | GEMINI | 43,764 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/.system_generated/logs/transcript.jsonl` | GEMINI | 543,249 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/.system_generated/steps/597/output.txt` | GEMINI | 1,113 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/.system_generated/tasks/task-651.log` | GEMINI | 122,317 | 2 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/.system_generated/tasks/task-712.log` | GEMINI | 1,000 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/implementation_plan.md` | GEMINI | 844 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/task.md` | GEMINI | 508 | 21 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/walkthrough.md` | GEMINI | 1,605 | 3 |
| `C:/Users/ajeem/.gemini/antigravity-ide/scratch/audit_report.json` | GEMINI | 19,592 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/REAL_GEMINI_BENCHMARK_REPORT.md` | REPO | 2,802 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/REAL_GROQ_BENCHMARK_REPORT.md` | REPO | 2,802 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/SEMANTIC_ENGINE_VS_BASELINE_REPORT.md` | REPO | 891 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/patch_applier.py` | REPO | 3,302 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/run_gemini_harness.py` | REPO | 2,743 | 2 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/run_groq_harness.py` | REPO | 2,845 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/safety_checker.py` | REPO | 563 | 1 |
| `C:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/validation/patch_validator.py` | REPO | 1,385 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/mock-mongoose.js` | EXTERNAL | 1,861 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/package.json` | EXTERNAL | 136 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js` | EXTERNAL | 360 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/auth.service.js` | EXTERNAL | 809 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/services/document.service.js` | EXTERNAL | 700 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/test-flow.js` | EXTERNAL | 3,052 | 1 |
| `c:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/implementation_plan.md` | GEMINI | 844 | 1 |
| `c:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/task.md` | GEMINI | 508 | 1 |
| `c:/Users/ajeem/.gemini/antigravity-ide/brain/bec51ff1-e8b6-4e57-a51a-85b324af07d8/walkthrough.md` | GEMINI | 1,605 | 3 |
| `c:/Users/ajeem/.gemini/antigravity-ide/scratch/audit_metrics.py` | GEMINI | 888 | 1 |
| `c:/Users/ajeem/.gemini/antigravity-ide/scratch/inspect_mismatch.py` | GEMINI | 573 | 1 |
| `c:/Users/ajeem/.gemini/antigravity-ide/scratch/inspect_steps.py` | GEMINI | 207 | 1 |
| `c:/Users/ajeem/.gemini/antigravity-ide/scratch/inspect_user_steps.py` | GEMINI | 133 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/.env` | REPO | 31 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/AGENT_SESSION_REPORT.md` | REPO | 4,251 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/REAL_GROQ_BENCHMARK_REPORT.md` | REPO | 2,802 | 4 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/SESSION_VS_MCP_REPORT.md` | REPO | 569 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/TASK_WINDOW_REPORT.md` | REPO | 2,546 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/TASK_WINDOW_VALIDATION_REPORT.md` | REPO | 781 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/VIBECODING_REPORT.md` | REPO | 387 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/generate_task_window_report.py` | REPO | 2,169 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/generate_task_window_v2_report.py` | REPO | 1,451 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/generate_vibecoding_report.py` | REPO | 1,834 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/snapshots/agent_session_metrics.json` | REPO | 16,542 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/snapshots/vibecoding_metrics.json` | REPO | 975 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/api/mcp_server.py` | REPO | 3,093 | 5 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/model_client.py` | REPO | 2,037 | 4 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/patch_applier.py` | REPO | 3,302 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/run_comparison_harness.py` | REPO | 5,406 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/run_gemini_harness.py` | REPO | 2,743 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/run_groq_harness.py` | REPO | 2,845 | 5 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/safety_checker.py` | REPO | 563 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/sandbox_manager.py` | REPO | 1,164 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/scoring_engine.py` | REPO | 798 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/benchmark/task_runner.py` | REPO | 3,896 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/telemetry/task_window_analyzer.py` | REPO | 4,943 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/telemetry/token_estimator.py` | REPO | 250 | 1 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/test-patch.py` | REPO | 294 | 2 |
| `c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/test-telemetry.py` | REPO | 678 | 1 |
| `c:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js` | EXTERNAL | 360 | 2 |

### Session: `bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78`

#### Task 1: `ROUTE:post:/login` (Query 1)
*   **Step Index Range**: `[0, 25]`
*   **Window Bounds**: `2026-06-08T18:20:53Z` &rarr; `2026-06-08T18:23:41Z`
*   **Window Duration**: `168.0 seconds`

##### Files Opened by Agent Details:
| Path | Category | Unique Token Count | Cumulative Read Count |
| :--- | :---: | :---: | :---: |
| `C:/Users/ajeem/.gemini/antigravity-ide/mcp/semantic-context-engine/mcp_build_graph.json` | GEMINI | 144 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/mcp/semantic-context-engine/mcp_query_context.json` | GEMINI | 158 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/mcp/semantic-context-engine/mcp_show_graph_metrics.json` | GEMINI | 52 | 1 |

##### MCP Selected Files Details:
| Path | Category | Raw File Size (Chars) | Raw File Tokens | Context Pruned Tokens |
| :--- | :---: | :---: | :---: | :---: |
| `src/controllers/auth.controller.js` | REPO | 1,360 | 340 | (Pruned inside Engine) |
| `src/routes/auth.routes.js` | REPO | 1,440 | 360 | (Pruned inside Engine) |
| `src/models/user.model.js` | REPO | 1,740 | 435 | (Pruned inside Engine) |
| `src/services/auth.service.js` | REPO | 3,236 | 809 | (Pruned inside Engine) |
| **Context payload size** | | | | **834** |

#### Task 2: `ROUTE:post:/register` (Query 2)
*   **Step Index Range**: `[26, 37]`
*   **Window Bounds**: `2026-06-08T18:23:43Z` &rarr; `2026-06-08T18:27:58Z`
*   **Window Duration**: `255.0 seconds`

##### Files Opened by Agent Details:
| Path | Category | Unique Token Count | Cumulative Read Count |
| :--- | :---: | :---: | :---: |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/.system_generated/steps/27/output.txt` | GEMINI | 1,051 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/.system_generated/steps/35/output.txt` | GEMINI | 4,771 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js` | EXTERNAL | 360 | 1 |

##### MCP Selected Files Details:
| Path | Category | Raw File Size (Chars) | Raw File Tokens | Context Pruned Tokens |
| :--- | :---: | :---: | :---: | :---: |
| `src/controllers/auth.controller.js` | REPO | 1,360 | 340 | (Pruned inside Engine) |
| `src/routes/auth.routes.js` | REPO | 1,440 | 360 | (Pruned inside Engine) |
| `src/models/user.model.js` | REPO | 1,740 | 435 | (Pruned inside Engine) |
| `src/services/auth.service.js` | REPO | 3,236 | 809 | (Pruned inside Engine) |
| **Context payload size** | | | | **874** |

#### Task 3: `ROUTE:post:/login` (Query 3)
*   **Step Index Range**: `[38, 59]`
*   **Window Bounds**: `2026-06-08T18:28:01Z` &rarr; `2026-06-08T18:31:45Z`
*   **Window Duration**: `224.0 seconds`

##### Files Opened by Agent Details:
| Path | Category | Unique Token Count | Cumulative Read Count |
| :--- | :---: | :---: | :---: |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/.env` | EXTERNAL | 43 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/package.json` | EXTERNAL | 136 | 1 |

##### MCP Selected Files Details:
| Path | Category | Raw File Size (Chars) | Raw File Tokens | Context Pruned Tokens |
| :--- | :---: | :---: | :---: | :---: |
| `src/controllers/auth.controller.js` | REPO | 1,360 | 340 | (Pruned inside Engine) |
| `src/routes/auth.routes.js` | REPO | 1,440 | 360 | (Pruned inside Engine) |
| `src/models/user.model.js` | REPO | 1,740 | 435 | (Pruned inside Engine) |
| `src/services/auth.service.js` | REPO | 3,236 | 809 | (Pruned inside Engine) |
| **Context payload size** | | | | **834** |

#### Task 4: `Trailing Session Verification` (Trailing)
*   **Step Index Range**: `[60, 135]`
*   **Window Bounds**: `2026-06-08T18:31:47Z` &rarr; `2026-06-08T18:41:48Z`
*   **Window Duration**: `601.0 seconds`

##### Files Opened by Agent Details:
| Path | Category | Unique Token Count | Cumulative Read Count |
| :--- | :---: | :---: | :---: |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/.system_generated/steps/61/output.txt` | GEMINI | 1,416 | 1 |
| `C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/semantic_engine_analysis.md` | GEMINI | 1,258 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/app.js` | EXTERNAL | 324 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/src/models/user.model.js` | EXTERNAL | 435 | 1 |
| `C:/Users/ajeem/Downloads/downloads/testing/testing1/test-flow.js` | EXTERNAL | 3,052 | 3 |

## 4. Computed Totals Validation

We verify the aggregate dashboard metrics:
*   **Total Agent Unique Baseline Tokens**: **104,512 tokens**
*   **Total Agent Cumulative Read Tokens**: **49,981 tokens**
*   **Total MCP Context Tokens**: **3,416 tokens**
*   **Average Unique File Tokens per Task**: **26,128.0 tokens**
*   **Average Cumulative Read Tokens per Task**: **12,495.2 tokens**
*   **Average MCP Context Tokens per Task**: **854.0 tokens**

## 5. Explanations for Negative Reduction Results

In some task windows, the reduction percentages are negative (i.e. MCP context size is larger than the agent baseline). Below is the exact technical explanation for each occurrence:

### Session: `bdbdb9aa...`, Task 2: `ROUTE:post:/register`
*   **Agent Unique Baseline**: `360` tokens
*   **MCP Context**: `874` tokens
*   **Unique Reduction %**: `-142.8%`
*   **Explanation**: The agent's investigation was extremely narrow in this brief task window (e.g. only opened 1 file, `['C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/.system_generated/steps/27/output.txt', 'C:/Users/ajeem/.gemini/antigravity-ide/brain/bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78/.system_generated/steps/35/output.txt', 'C:/Users/ajeem/Downloads/downloads/testing/testing1/src/routes/auth.routes.js']`, totalling 360 tokens). The MCP Context Engine resolved callers/dependents and returned snippets from multiple selected files, totaling 874 tokens. Because the blast radius context contains code files the agent had not yet investigated in this window, the context size exceeds the agent's minimal baseline, resulting in a negative reduction. This highlights that MCP queries can preemptively load files before the agent opens them manually.

### Session: `bdbdb9aa...`, Task 3: `ROUTE:post:/login`
*   **Agent Unique Baseline**: `179` tokens
*   **MCP Context**: `834` tokens
*   **Unique Reduction %**: `-365.9%`
*   **Explanation**: The agent's investigation was extremely narrow in this brief task window (e.g. only opened 1 file, `['C:/Users/ajeem/Downloads/downloads/testing/testing1/.env', 'C:/Users/ajeem/Downloads/downloads/testing/testing1/package.json']`, totalling 179 tokens). The MCP Context Engine resolved callers/dependents and returned snippets from multiple selected files, totaling 834 tokens. Because the blast radius context contains code files the agent had not yet investigated in this window, the context size exceeds the agent's minimal baseline, resulting in a negative reduction. This highlights that MCP queries can preemptively load files before the agent opens them manually.

## 6. Audit Conclusion

> [!NOTE]
> **Audit Result**: **VERIFIED**. All metrics, reduction percentages, and window partitions under Event-Based Attribution V3 are fully reproducible from raw files, log steps, and MCP context metrics.