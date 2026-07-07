# Tree-sitter Query Guide - Semantic Context Engine

This document provides complete details on the SCM query system, naming conventions, and AST classification mappings used in the Semantic Context Engine.

---

## 1. Naming & Capture Conventions

SCM files define specific capture anchors using the `@` character. The classification engine (`classify_match()`) expects exact capture tags to map nodes into semantic models:

| Capture Tag | Classification Target | Purpose |
| :--- | :--- | :--- |
| `@import.source` / `@import.alias` | `IMPORT` | ESM imports, namespace imports, CommonJS `require()` |
| `@endpoint.served_route` / `@router.obj` | `ROUTE` | Express routers, verbs, middlewares, controller bindings |
| `@taint.source` | `UNKNOWN` (used as property) | Direct request bodies/queries (`req.body`, `req.query`) |
| `@db.model` / `@db.operation` | `DATABASE` | Mongoose find, delete operations, raw SQL query anchors |
| `@function.name` / `@function.node` | `FUNCTION_DEF` | AST function declaration, arrow/pair definitions |
| `@param.name` / `@param.destructured` | `FUNCTION_PARAMS` | Positional and destructured parameters |
| `@call.func_name` / `@call.obj_name` | `CALL` | Standard member expressions and function call nodes |
| `@arg.value` | `CALL_ARGUMENTS` | Expressions passed inside positional parentheses |
| `@assign.variable` / `@assign.value` | `VARIABLE_ASSIGNMENT` | Scoped and global assignments |
| `@return.value` | `RETURN_VALUE` | Returned expressions |
| `@error.throw` | `ERROR` | Throw statements |
| `@contract.name` | `CONTRACT` | Validation schemas (e.g. Joi, Zod) |

---

## 2. Query Mappings & Examples

Below are standard patterns defined in `src/queries/javascript.scm` demonstrating how queries are structured and matched against the AST:

### A. Route Extraction
Traces Express routing verbs and middleware chains:
```scm
(call_expression
  function: (member_expression
    object: (identifier) @router.obj
    property: (property_identifier) @endpoint.served_method
  )
  arguments: (arguments
    (string (string_fragment) @endpoint.served_route)
    (_) @route.handler ; Catches middlewares and final controller
  )
  (#match? @endpoint.served_method "^(get|post|put|delete|patch|options|use|all)$")
)
```

### B. Function Parameters
Matches identifiers listed inside function parameter nodes:
```scm
[
  (function_declaration parameters: (formal_parameters (identifier) @param.name))
  (method_definition parameters: (formal_parameters (identifier) @param.name))
  (pair value: (arrow_function parameters: (formal_parameters (identifier) @param.name)))
  (variable_declarator value: (arrow_function parameters: (formal_parameters (identifier) @param.name)))
]
```

### C. Member Call Expressions
Captures calls like `userService.fetchUsers(safeEmail)`:
```scm
(call_expression
  function: [
    (identifier) @call.func_name
    (member_expression
      object: (_) @call.obj_name
      property: (property_identifier) @call.func_name
    )
  ]
) @call.node
```

### D. Returns
Matches the direct child of return statements:
```scm
(return_statement
  (_) @return.value
)
```

---

## 3. Classifier Mapping Rules

When a match contains a set of captures, `classify_match()` inside `src/semantic_core/match_classifier.py` checks for specific key presences. The order of evaluation ensures precise taxonomy:

```python
def classify_match(capture_names):
    capture_set = set(capture_names)
    
    # 1. Routes check
    if "endpoint.served_route" in capture_set and "endpoint.served_method" in capture_set:
        return "ROUTE"

    # 2. Imports check
    if "import.source" in capture_set:
        return "IMPORT"

    # 3. Database operations
    if "db.operation" in capture_set:
        return "DATABASE"

    # 4. Parameters (Checks for param.name presence)
    if "param.name" in capture_set:
        return "FUNCTION_PARAMS"

    # 5. Variable Assignments
    if "assign.variable" in capture_set and "assign.value" in capture_set:
        return "VARIABLE_ASSIGNMENT"

    # 6. Call Arguments
    if "arg.value" in capture_set:
        return "CALL_ARGUMENTS"

    # 7. Calls
    if "call.func_name" in capture_set:
        return "CALL"
    
    ...
```
