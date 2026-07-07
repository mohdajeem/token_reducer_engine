# Data Flow Engine - Semantic Context Engine

This document outlines the design and operational logic of the **Data Flow Engine** inside the Semantic Context Engine. The Data Flow Engine maps the deterministic propagation of data across scopes, assignments, and boundaries.

---

## 1. Data Flow Mapping Lifecycle

Data flows are traced using the following propagation pipeline:

```mermaid
graph TD
    Assignment[1. Variable Assignment: const safe = req.body]
    --> Argument[2. Call Site Argument: myFunction(safe)]
    
    Argument
    --> ParamMapping[3. Compiler parameter join: safe -> parameter]
    
    ParamMapping
    --> ReturnProp[4. Return statement matching: return value]
    
    ReturnProp
    --> CrossFlow[5. Call site return propagation]
```

### Diagram Description & Details

*   **Purpose**: Illustrates the lifecycle of data flow mapping, tracing variables from their initial assignments to call arguments, formal parameters, and return statements.
*   **Components**:
    *   *Variable Assignment*: Ingests LHS (variable) and RHS (source/value) assignments.
    *   *Argument Call Site*: Captures variables passed to function invocations.
    *   *Parameter Mapping*: Matches call site arguments to callee formal parameters positionally.
    *   *Return Statement*: Traces return values inside function blocks.
    *   *Return Propagation*: Propagates data values back to caller receiving scopes.
*   **Execution Flow**: Variable Assignment ➔ Call Site Argument Passing ➔ Compiler Parameter Index Join ➔ Return Statement Analysis ➔ Caller Return Propagation.
*   **Important Notes**: Supports tracking implicit and explicit flows, enabling deep static data tracking and taint resolution across multiple modules.

---

## 2. Core Engine Mechanisms

### A. Variable Assignments (`track_variable_states`)
*   **Role**: Tracks standard and sanitized scoped variable values.
*   **Mechanism**: Scans all `VARIABLE_ASSIGNMENT` matches:
    *   Saves the assignment variable name, value, and scope.
    *   If the assignment contains a user input token (e.g. `req.body`), it flags the variable as `tainted`.
    *   If the assignment contains a sanitizer token (e.g. `escape()`), it flags the variable as `sanitized` (and untainted).
*   **Output**: Saved inside `self.graph["variable_states"]`.

### B. Argument-Parameter Mapping (`build_argument_parameter_flow`)
*   **Role**: Maps parameters passed at call sites to their target function parameter names:
*   **Mechanism**: Runs after imports and functions have been fully compiled:
    *   Iterates through all resolved `calls`.
    *   Finds arguments registered for the specific `call_id`.
    *   Finds parameters registered for the target function name inside the target file.
    *   Performs a index-by-index matching join:
        ```python
        for i in range(min(len(arguments), len(parameters))):
            self.graph["data_flow"].append({
                "source": arguments[i],
                "target_file": target_file,
                "target_function": target_function,
                "target_param": parameters[i]
            })
        ```

### C. Return Value Propagation (`propagate_return_taint`)
*   **Role**: Traces taint values flowing back out of returned statements:
*   **Mechanism**:
    *   Looks up return values registered under `self.graph["returns"]`.
    *   Checks if the returned value matches the `target_param` of any `data_flow` call site.
    *   If so, it appends a `RETURN_TAINT` source mapping the source taint back to the caller's target.

---

## 3. Current Limitations & Gaps

While the Data Flow Engine is extremely precise for standard procedural workflows, there are several known limitations:
1.  **Positional-Only Parameter Joins**: Parameter joins assume strict positional ordering (e.g. argument 1 maps to parameter 1). If the target language implements keyword arguments or rest/destructured object arguments (e.g. `myFunction({ email, password })`), the join index matching is incomplete.
2.  **No Deep Object Tracking**: The engine tracks the outer variable (e.g. `req.body.email` or `user`), but does not perform deep structure tracking for property reassignments (e.g. `user.email = rawEmail`).
3.  **Dynamic Call Limitations**: If a function is invoked dynamically or passed as a callback (e.g. `app.use(myHandler)`), and cannot be resolved statically through import lookups, the data flow mapping is skipped.
