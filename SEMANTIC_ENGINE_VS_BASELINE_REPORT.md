# Benchmark Report: Semantic Context Engine vs Raw Repository Baseline

**Execution Date:** 2026-06-09 23:44:06
**Evaluated Model:** `llama-3.1-8b-instant` (Groq API Client)

## Executive Summary

This report compares the performance of an AI coding agent under two distinct context-gathering strategies:
1.  **Mode A (Baseline)**: Sending a raw subset of all files within the repository (`src/` JS files up to context limit).
2.  **Mode B (Semantic Engine)**: Querying the local semantic MCP server's `mcp_query_context` targeting the blast-radius slices.

To enforce safety, all tests are executed as static, rule-based Python AST and codebase assertions (no `.js` scripts are run on the system).

---

## 📊 Side-by-Side Comparison Dashboard

| Task | Metric | Mode A (Baseline) | Mode B (Semantic Engine) | Delta / Benefit |
| :--- | :--- | :---: | :---: | :---: |
| **Add rate limiting to login** | Tokens Sent | 5258 | 1163 | **-4095 tokens** (77.9% reduction) |
| | Tokens Received | 0 | 216 | +216 tokens |
| | API Latency | 0.00s | 1.15s | +1.15s |
| | Estimated Cost | $0.000263 | $0.000075 | **-$0.000187** |
| | AST Parse Valid | `False` | `True` | Semantic Engine Fixed AST |
| | Functional Verification | `FAILED` | `PASSED` | Semantic Engine Resolved Task |
| | Edit Recall | 100.0% | 100.0% | +0.0% |
| | Edit Precision | 9.1% | 25.0% | **+15.9%** (Higher Precision) |
| | | | | |
| **Add audit logging for document uploads** | Tokens Sent | 5206 | 258 | **-4948 tokens** (95.0% reduction) |
| | Tokens Received | 0 | 289 | +289 tokens |
| | API Latency | 0.00s | 1.57s | +1.57s |
| | Estimated Cost | $0.000260 | $0.000036 | **-$0.000224** |
| | AST Parse Valid | `False` | `True` | Semantic Engine Fixed AST |
| | Functional Verification | `FAILED` | `FAILED` | Both Failed |
| | Edit Recall | 100.0% | 0.0% | -100.0% |
| | Edit Precision | 9.1% | 0.0% | **-9.1%** (Higher Precision) |
| | | | | |
| **Add forgot password flow** | Tokens Sent | 5286 | 1190 | **-4096 tokens** (77.5% reduction) |
| | Tokens Received | 1654 | 682 | -972 tokens |
| | API Latency | 13.45s | 1.44s | -12.01s |
| | Estimated Cost | $0.000397 | $0.000114 | **-$0.000283** |
| | AST Parse Valid | `True` | `True` | Consistent |
| | Functional Verification | `FAILED` | `FAILED` | Both Failed |
| | Edit Recall | 100.0% | 100.0% | +0.0% |
| | Edit Precision | 27.3% | 75.0% | **+47.7%** (Higher Precision) |
| | | | | |

## 📈 Aggregated Comparison

| Aggregate Metric | Mode A (Baseline) | Mode B (Semantic Engine) | Benefit / Delta |
| :--- | :---: | :---: | :--- |
| **Total Input Tokens** | 15750 | 2611 | **-13139 tokens** (83.4% saved) |
| **Average Context Precision** | 15.2% | 33.3% | **+18.2%** |
| **Functional Pass Rate** | 0.0% | 33.3% | **+33.3%** |
| **Total Task Cost** | $0.000920 | $0.000226 | **-$0.000694** (75.5% cheaper) |

## 🔍 Task-Specific Breakdown

### Task: Add rate limiting to login (task_rate_limiting)

#### Mode A (Baseline) Response Patch
```text
Not generated or failed syntax
```

#### Mode B (Semantic) Response Patch
```text
Syntax Valid & Applied Successfully
```

### Task: Add audit logging for document uploads (task_audit_logging)

#### Mode A (Baseline) Response Patch
```text
Not generated or failed syntax
```

#### Mode B (Semantic) Response Patch
```text
Syntax Valid & Applied Successfully
```

### Task: Add forgot password flow (task_forgot_password)

#### Mode A (Baseline) Response Patch
```text
Syntax Valid & Applied Successfully
```

#### Mode B (Semantic) Response Patch
```text
Syntax Valid & Applied Successfully
```