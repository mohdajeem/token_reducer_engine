; =============================================================================
; 1. IMPORTS (ESM & CommonJS)
; =============================================================================

; ES6: import x from 'y'
(import_statement
  (import_clause
    (identifier) @import.alias)
  (string (string_fragment) @import.source)
)

; ES6: import { x as y } from 'z'
(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @import.name
        alias: (identifier)? @import.alias)))
  (string (string_fragment) @import.source)
)

; ES6: import * as x from 'y'
(import_statement
  (import_clause
    (namespace_import (identifier) @import.alias))
  (string (string_fragment) @import.source)
)

; CommonJS: const x = require('y')
(variable_declarator
  name: (identifier) @import.alias
  value: (call_expression
    function: (identifier) @req (#eq? @req "require")
    arguments: (arguments (string (string_fragment) @import.source))
  )
)

; CommonJS: const { x, y } = require('z')
(variable_declarator
  name: (object_pattern) @import.destructure
  value: (call_expression
    function: (identifier) @req (#eq? @req "require")
    arguments: (arguments (string (string_fragment) @import.source))
  )
)

; =============================================================================
; 2. ROUTES & MIDDLEWARES
; =============================================================================

(call_expression
  function: (member_expression
    object: (identifier) @router.obj
    property: (property_identifier) @endpoint.served_method
  )
  arguments: (arguments
    (string (string_fragment) @endpoint.served_route)
    (_) @route.handler ; Catches middlewares and the final controller
  )
  (#match? @endpoint.served_method "^(get|post|put|delete|patch|options|use|all)$")
)

; Chainable routes - Depth 1 (e.g. router.route('/path').get(handler))
(call_expression
  function: (member_expression
    object: (call_expression
      function: (member_expression
        object: (identifier) @router.obj
        property: (property_identifier) @route_method (#eq? @route_method "route")
      )
      arguments: (arguments (string (string_fragment) @endpoint.served_route))
    )
    property: (property_identifier) @endpoint.served_method
  )
  (#match? @endpoint.served_method "^(get|post|put|delete|patch|options|use|all)$")
)

; Chainable routes - Depth 2 (e.g. router.route('/path').post(m).get(handler))
(call_expression
  function: (member_expression
    object: (call_expression
      function: (member_expression
        object: (call_expression
          function: (member_expression
            object: (identifier) @router.obj
            property: (property_identifier) @route_method (#eq? @route_method "route")
          )
          arguments: (arguments (string (string_fragment) @endpoint.served_route))
        )
        property: (property_identifier) @endpoint.served_method_inner1
      )
    )
    property: (property_identifier) @endpoint.served_method
  )
  (#match? @endpoint.served_method "^(get|post|put|delete|patch|options|use|all)$")
)

; Chainable routes - Depth 3 (e.g. router.route('/path').get(h1).put(h2).delete(h3))
(call_expression
  function: (member_expression
    object: (call_expression
      function: (member_expression
        object: (call_expression
          function: (member_expression
            object: (call_expression
              function: (member_expression
                object: (identifier) @router.obj
                property: (property_identifier) @route_method (#eq? @route_method "route")
              )
              arguments: (arguments (string (string_fragment) @endpoint.served_route))
            )
            property: (property_identifier) @endpoint.served_method_inner1
          )
        )
        property: (property_identifier) @endpoint.served_method_inner2
      )
    )
    property: (property_identifier) @endpoint.served_method
  )
  (#match? @endpoint.served_method "^(get|post|put|delete|patch|options|use|all)$")
)

; =============================================================================
; 3. TAINT SOURCES (req.body, req.query, req.params, req.headers)
; =============================================================================

(member_expression
  object: (identifier) @req.obj
  property: (property_identifier) @req.prop
  (#match? @req.obj "^req$")
  (#match? @req.prop "^(body|query|params|headers)$")
)

(member_expression
  object: (member_expression
    object: (identifier) @req.obj
    property: (property_identifier) @req.prop
  )
  property: (property_identifier) @req.field
  (#match? @req.obj "^req$")
  (#match? @req.prop "^(body|query|params|headers)$")
)

; =============================================================================
; 4. DATABASE SINKS (Mongoose & Raw SQL)
; =============================================================================

(call_expression
  function: (member_expression
    object: (identifier) @db.model
    property: (property_identifier) @db.operation)
  (#match? @db.operation "^(find|findOne|findMany|create|update|delete|save)$")
)

(call_expression
  function: (member_expression
    object: (member_expression
      object: (_) @call.obj_name
      property: (property_identifier) @db.model)
    property: (property_identifier) @db.operation)
  (#match? @db.operation "^(find|findOne|findMany|create|update|delete|save)$")
)




; =============================================================================
; 5. FUNCTION DEFINITIONS & PARAMETERS
; =============================================================================

(function_declaration
  name: (identifier) @function.name
) @function.node

(variable_declarator
  name: (identifier) @function.name
  value: [
    (arrow_function)
    (function_expression)
  ]
) @function.node


; Object-literal members are functions ONLY when their value is one. The unconstrained
; form registered every `key: value` (config keys, string props) as a function -- on
; markedjs/marked that was 1046 "functions" with 154 unique names.
(pair
  key: (property_identifier) @function.name
  value: [
    (arrow_function)
    (function_expression)
  ]
) @function.node

; Prototype-based classes: `p5.prototype.loadStrings = function () {...}` -- the entire
; public API of processing/p5.js (357 definitions in src/, 3 were captured before).
; The owning class (`p5`) is recovered from the AST in the match extractor.
(assignment_expression
  left: (member_expression
    object: (identifier) @static.owner
    property: (property_identifier) @function.name)
  right: [
    (arrow_function)
    (function_expression)
  ]
) @function.node

(assignment_expression
  left: (member_expression
    object: (member_expression
      property: (property_identifier) @proto (#eq? @proto "prototype"))
    property: (property_identifier) @function.name)
  right: [
    (arrow_function)
    (function_expression)
  ]
) @function.node

(method_definition
  name: (property_identifier) @function.name
) @function.node



; Test callbacks are anonymous; register them as functions named by their title so a
; failing test id maps to a graph node and `mcp_tests_for` can name the test.
(call_expression
  function: (identifier) @test.runner (#match? @test.runner "^(it|test|describe|suite|context|specify)$")
  arguments: (arguments
    (string (string_fragment) @function.name)
    [
      (arrow_function)
      (function_expression)
    ])
) @function.node

; standard parameters: (req, res)
(formal_parameters (identifier) @param.name)

; default parameters: (req = {})
(formal_parameters (assignment_pattern left: (identifier) @param.name))

; rest parameters: (...args)
(formal_parameters (rest_pattern (identifier) @param.rest))

; destructured parameters: ({ name, email: userEmail, ...rest }, res)
(object_pattern (shorthand_property_identifier_pattern) @param.destructure_prop)
(object_pattern (pair_pattern key: (property_identifier) @param.destructure_key value: (identifier) @param.destructure_prop))
(object_pattern (rest_pattern (identifier) @param.destructure_rest))



; =============================================================================
; 6. CALLS, ARGUMENTS & CORE LOGIC
; =============================================================================

(call_expression
  function: (identifier) @call.func_name
)

; `handlers[type](e)` / `table.get(k)(x)`: computed callee -> dispatch-table edges
(call_expression
  function: (subscript_expression) @call.dispatch
)
(call_expression
  function: (call_expression) @call.dispatch
)

(call_expression
  function: (member_expression
    object: (_) @call.obj_name
    property: (property_identifier) @call.func_name
  )
)


(call_expression
  arguments: (arguments (_) @arg.value)
)

; `new X()` is a call of X's constructor: it gets a call record (resolved to the class
; node, plus a constructor edge) so changing a constructor shows every instantiation.
(new_expression
  constructor: (identifier) @call.new_class
)

; Class declarations become class nodes (kind="class") so `new X()` / `X()` resolve to
; them even when X has no methods, and the superclass is known for `super` / inheritance.
(class_declaration
  name: (identifier) @class.name
  (class_heritage)? @class.heritage
) @class.node
(class
  name: (identifier) @class.name
  (class_heritage)? @class.heritage
) @class.node

; =============================================================================
; 7. VARIABLES, ALIASES & DESTRUCTURING
; =============================================================================

(variable_declarator
  name: (identifier) @assign.variable
  value: (_) @assign.value
)

(variable_declarator
  name: (object_pattern
    (shorthand_property_identifier_pattern) @destructure.name
  )
  value: (identifier) @destructure.source
)

; =============================================================================
; 8. CONTRACTS (Joi, Zod Validation Schemas)
; =============================================================================

(variable_declarator
  name: (identifier) @contract.name
  value: (call_expression
    function: (member_expression
      object: (identifier) @contract.lib
    )
    (#match? @contract.lib "^(Joi|z|yup)$")
  )
)

; =============================================================================
; 9. ERRORS & RETURNS
; =============================================================================

(throw_statement
  [
    (new_expression constructor: (identifier) @error.throw)
    (identifier) @error.throw
  ]
)

(return_statement
  (_) @return.value
)

; =============================================================================
; 10. EXPORTS (ESM & CommonJS)
; =============================================================================

; ES6
(export_statement
  declaration: [
    (function_declaration name: (identifier) @export.name)
    (class_declaration name: (identifier) @export.name)
    (variable_declaration (variable_declarator name: (identifier) @export.name))
  ]
)

; Re-exports (barrel files): `export * from './core'` / `export { a as b } from './x'`.
; Followed at call-resolution time so `import { boot } from './index'` reaches the file
; that actually defines boot.
(export_statement
  (string (string_fragment) @reexport.source)
) @reexport.node

; CommonJS: module.exports = app
(assignment_expression
  left: (member_expression
    object: (identifier) @mod (#eq? @mod "module")
    property: (property_identifier) @exp (#eq? @exp "exports")
  )
  right: (identifier) @export.name
)

; =============================================================================
; 11. REACT JSX COMPONENTS & PROPS
; =============================================================================

(jsx_opening_element name: (identifier) @jsx.component)
(jsx_self_closing_element name: (identifier) @jsx.component)
(jsx_attribute (property_identifier) @jsx.prop_name)