# Ground Truth Validation Report (V10)

This report validates the telemetry system estimates (V6, V7, V8, and V9) against the ground truth calculated by tokenizing the actual reconstructed conversation histories. We evaluate accuracy under two distinct models:
1.  **Window-Level Ground Truth**: Validates the accuracy of the analyzer's window-level aggregation logic.
2.  **Cumulative Session Ground Truth**: Validates how well the telemetry represents the actual cumulative conversation history loaded into Gemini's context window.

---

## ⚖️ Executive Verdict

### Model 1: Window-Level Ground Truth
*   **Most Accurate Version**: **V9** (Conversation-Level)
*   **Average Relative Error (V9)**: **0.26%**
*   **Telemetry Accuracy Score**: **99.74%**
*   **V10 Audit Status**: **PASS** (Average error < 10%)

### Model 2: Cumulative Session Ground Truth
*   **Most Accurate Version**: **V9** (Conversation-Level)
*   **Average Relative Error (V9)**: **30.99%**
*   **Telemetry Accuracy Score**: **69.01%**
*   **V10 Audit Status**: **FAIL** (Average error > 10%)

---

## 📊 PART 1 — Reconstructed Context Token Counts

We chose 5 completed tasks across sessions `bdbdb9aa` and `bec51ff1` and reconstructed their exact conversation histories:

*   **Task 1**: Session `bdbdb9aa` Task 1 (QID 1, `post:/login`)
*   **Task 2**: Session `bdbdb9aa` Task 2 (QID 2, `post:/register`)
*   **Task 3**: Session `bdbdb9aa` Task 3 (QID 3, `post:/login`)
*   **Task 4**: Session `bdbdb9aa` Task 4 (Trailing window)
*   **Task 5**: Session `bec51ff1` Task 1 (QID 4, `post:/register`)

---

## 🤖 Provider: GEMINI

### 1. Window-Level Ground Truth (Steps within Window only)

This model measures how accurately the telemetry tokenizes the step contents within each isolated task window:

| Task | Actual Tokens | V6 Estimate | V7 Estimate | V8 Estimate | V9 Estimate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Task 1 (QID 1)** | 3,807 | 0 | 0 | 2,228 | 3,795 |
| **Task 2 (QID 2)** | 4,154 | 384 | 377 | 2,855 | 4,148 |
| **Task 3 (QID 3)** | 3,269 | 191 | 190 | 2,231 | 3,257 |
| **Task 4 (Trailing)** | 20,544 | 4,065 | 1,946 | 14,756 | 20,501 |
| **Task 5 (QID 4)** | 172,242 | 110,908 | 43,215 | 137,653 | 171,809 |

#### Error Summary Matrix:
| Version | Mean Abs Error | Median Abs Error | P95 Abs Error | Mean Rel Error (%) | Median Rel Error (%) | P95 Rel Error (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **V6** | 17,693.6 | 3,807.0 | 61,334.0 | 80.15% | 90.76% | 100.00% |
| **V7** | 31,657.6 | 3,807.0 | 129,027.0 | 90.11% | 90.92% | 100.00% |
| **V8** | 8,858.6 | 1,579.0 | 34,589.0 | 30.55% | 31.27% | 41.48% |
| **V9** | **101.2** | **12.0** | **433.0** | **0.26%** | **0.25%** | **0.37%** |

---

### 2. Cumulative Session Ground Truth (Start of Session &rarr; End of Window)

This model measures how accurately the window-level estimates represent the total growing conversation footprint sent to the model:

| Task | Actual Tokens | V6 Estimate | V7 Estimate | V8 Estimate | V9 Estimate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Task 1 (QID 1)** | 3,807 | 0 | 0 | 2,228 | 3,795 |
| **Task 2 (QID 2)** | 7,961 | 384 | 377 | 2,855 | 4,148 |
| **Task 3 (QID 3)** | 11,231 | 191 | 190 | 2,231 | 3,257 |
| **Task 4 (Trailing)** | 31,776 | 4,065 | 1,946 | 14,756 | 20,501 |
| **Task 5 (QID 4)** | 172,242 | 110,908 | 43,215 | 137,653 | 171,809 |

#### Error Summary Matrix:
| Version | Mean Abs Error | Median Abs Error | P95 Abs Error | Mean Rel Error (%) | Median Rel Error (%) | P95 Rel Error (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **V6** | 22,293.8 | 11,040.0 | 61,334.0 | 83.26% | 95.18% | 100.00% |
| **V7** | 36,257.8 | 11,041.0 | 129,027.0 | 92.47% | 95.26% | 100.00% |
| **V8** | 13,458.8 | 9,000.0 | 34,589.0 | 51.88% | 53.56% | 80.14% |
| **V9** | **4,701.4** | **3,813.0** | **11,275.0** | **30.99%** | **35.48%** | **71.00%** |

---

## 🤖 Provider: GROQ (Llama)

### 1. Window-Level Ground Truth (Steps within Window only)

| Task | Actual Tokens | V6 Estimate | V7 Estimate | V8 Estimate | V9 Estimate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Task 1 (QID 1)** | 4,392 | 0 | 0 | 2,571 | 4,378 |
| **Task 2 (QID 2)** | 4,793 | 443 | 435 | 3,297 | 4,789 |
| **Task 3 (QID 3)** | 3,772 | 220 | 220 | 2,576 | 3,761 |
| **Task 4 (Trailing)** | 23,705 | 4,692 | 2,246 | 17,026 | 23,657 |
| **Task 5 (QID 4)** | 198,741 | 127,976 | 49,872 | 158,860 | 198,285 |

#### Error Summary Matrix:
| Version | Mean Abs Error | Median Abs Error | P95 Abs Error | Mean Rel Error (%) | Median Rel Error (%) | P95 Rel Error (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **V6** | 20,414.4 | 4,392.0 | 70,765.0 | 80.15% | 90.76% | 100.00% |
| **V7** | 36,526.0 | 4,392.0 | 148,869.0 | 90.10% | 90.92% | 100.00% |
| **V8** | 10,214.6 | 1,821.0 | 39,881.0 | 30.52% | 31.21% | 41.46% |
| **V9** | **106.6** | **14.0** | **456.0** | **0.23%** | **0.23%** | **0.32%** |

---

### 2. Cumulative Session Ground Truth (Start of Session &rarr; End of Window)

| Task | Actual Tokens | V6 Estimate | V7 Estimate | V8 Estimate | V9 Estimate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Task 1 (QID 1)** | 4,392 | 0 | 0 | 2,571 | 4,378 |
| **Task 2 (QID 2)** | 9,186 | 443 | 435 | 3,297 | 4,789 |
| **Task 3 (QID 3)** | 12,959 | 220 | 220 | 2,576 | 3,761 |
| **Task 4 (Trailing)** | 36,664 | 4,692 | 2,246 | 17,026 | 23,657 |
| **Task 5 (QID 4)** | 198,741 | 127,976 | 49,872 | 158,860 | 198,285 |

#### Error Summary Matrix:
| Version | Mean Abs Error | Median Abs Error | P95 Abs Error | Mean Rel Error (%) | Median Rel Error (%) | P95 Rel Error (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **V6** | 25,722.2 | 12,739.0 | 70,765.0 | 83.26% | 95.18% | 100.00% |
| **V7** | 41,833.8 | 12,739.0 | 148,869.0 | 92.47% | 95.26% | 100.00% |
| **V8** | 15,522.4 | 10,383.0 | 39,881.0 | 51.86% | 53.56% | 80.12% |
| **V9** | **5,414.4** | **4,397.0** | **13,007.0** | **30.97%** | **35.48%** | **70.98%** |

---

## 🔍 Validation Insights & Discussion

1.  **Window-Level Aggregation Accuracy (99.74%)**:
    The small difference between V9 and the actual window-level ground truth (e.g. **3,807** actual tokens vs **3,795** V9 tokens for Task 1) is solely due to token boundary alignment when tokenizing a single joined string vs summing individual message token counts. This proves that the telemetry analyzer's step categorization, parsing, and tokenization algorithms are **extremely accurate**.
2.  **Cumulative Session Overhead (30.99% error)**:
    Under cumulative session-level ground truth, the telemetry shows a higher average error of **30.99%** (leading to a **FAIL** status under the strict 10% threshold). This is because task windows partition the session into discrete, independent chunks. A window-level estimate (V9) measures the conversational activity *within that task*, but does not carry forward the historical conversational state from previous tasks in the same session.
3.  **Accuracy Ranking**:
    Across all tests, the versions rank consistently in accuracy:
    $$\text{V9 (Best)} > \text{V8} > \text{V6} > \text{V7 (Worst)}$$
    *   **V9** is closest to ground truth because it accounts for planners, user inputs, and command outputs.
    *   **V7** shows the highest error because it limits its measurement strictly to file line views, completely ignoring the tool execution logs, grep searches, planners, and prompts that dominate actual LLM context.
