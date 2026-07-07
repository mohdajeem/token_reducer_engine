# AI Benchmark Harness V1: Evaluation Report

Generated on: 2026-06-09 22:54:37
Evaluated Model: `mock-model`

## 📊 Global Dashboard

| Metric | Average Score | Description |
| :--- | :---: | :--- |
| **Test Pass Rate (Accuracy)** | **100.0%** | Percentage of tasks that successfully pass all unit tests. |
| **Edit Recall** | **100.0%** | Percentage of ground-truth files successfully context-extracted. |
| **Edit Precision** | **100.0%** | Tightness of context selection. |
| **Context Efficiency** | **84.5%** | Percentage of codebase tokens pruned. |
| **Hallucination Rate** | **0.0%** | Ratio of unresolved symbol references introduced by patch. |
| **Total API Cost** | **$0.000000** | Total token billing based on pricing model. |
| **Average Latency** | **0.00s** | Average model inference wait time. |

---
## 📋 Task Evaluation Summary

| Task Name | Policy | Recall | Precision | Safety Score | Test Passed | Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Modify getUserById in microservice | `84.5%` | 100% | 100% | 0.0% | 🟢 PASS | 0.00s |

---
## 🔍 Detailed Task Logs

### Modify getUserById in microservice
- **Task ID**: `task_modify_get_user`
- **Context Characters**: `233` (~58 tokens)
- **AST Validation Status**: `Valid`
- **Findings/Violations Detected**: None

**Test Log Snippet**:
```text
STDOUT:
PASSED - getUserById return value updated successfully


STDERR:

```
