# Current Limitations - Semantic Context Engine

This document provides an honest assessment of the known weaknesses, architectural debts, and functional limitations currently present in the Semantic Context Engine.

---

## 1. Static Linkage Limitations

Because static analysis operates without executing the code, there are several standard dynamic patterns the engine cannot resolve:

### A. Dynamic Imports & Code Splitting
*   **Limitation**: If imports are resolved dynamically (e.g. `import(someVar)` or `require(dynamicPath)`), the engine cannot statically track their targets.
*   **Impact**: These modules are omitted from the [Symbol Table](file:///c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system/src/semantic_core/symbol_table.py), preventing `FUNCTION_CALL` execution edges from being compiled.

### B. Callback & Event-Driven Flows
*   **Limitation**: Tracing arguments passed inside callback functions (e.g. `array.map(item => process(item))`) or event emitters (e.g. `emitter.emit('event', data)`) is incomplete.
*   **Impact**: Taint propagation across dynamic callback parameters is occasionally lost.

---

## 2. Data Flow & Typing Constraints

*   **No Strong Type Systems**: The engine does not run type inference. It maps symbol names literally. If there are multiple functions with the name `find()` across different database classes (e.g. `User.find()` and `Product.find()`), the resolver relies on local alias registry tables, which can lead to ambiguity if type information is completely missing.
*   **Positional-Only Parameter Joins**: Parameter flow mappings in `build_argument_parameter_flow()` assume strict positional arrays (e.g. argument 1 maps to parameter 1). If the code implements keyword bindings, default parameters, rest arguments (e.g. `...args`), or object destructuring at parameter sites (e.g. `function save({ email, name })`), parameter mapping joins are incomplete.

---

## 3. Scope Tracking Ambiguities

*   **Global Variables Context Collision**: Global variable assignments are recorded under `"GLOBAL_SCOPE"`. If multiple files define identical global variable names (e.g., `const config = ...`), they are grouped under `"GLOBAL_SCOPE"`. While the file path separates them in the variable database structure, resolving taint flows can experience name collision if paths are resolved generically.
*   **Prototype & Class Inheritances**: Standard JS prototype-based inheritance and method overriding are not deeply resolved. Class-level member variables (e.g. `this.password = req.body.password`) are tracked in assignments but not traced through deep object paths.

---

## 4. Current Architectural Debt

*   **File-level Invalidation**: The incremental compiler invalidates entire file nodes on a change. For high-frequency, real-time IDE typing, invalidating only the changed function (function-level invalidation) is much more efficient.
*   **Single-Threaded Parser Walking**: Walking and parsing directories is single-threaded. For massive repositories (>10,000 files), this should be parallelized using multi-processing or worker threads.
