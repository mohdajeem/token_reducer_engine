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
  (#eq? @req.obj "req")
  (#match? @req.prop "^(body|query|params|headers)$")
) @taint.source

(member_expression
  object: (member_expression
    object: (identifier) @req.obj
    property: (property_identifier) @req.prop
  )
  property: (property_identifier) @req.field
  (#eq? @req.obj "req")
  (#match? @req.prop "^(body|query|params|headers)$")
) @taint.source

; =============================================================================
; 4. DATABASE SINKS (Mongoose & Raw SQL)
; =============================================================================

(call_expression
  function: (member_expression
    object: [
      (identifier) @db.model
      (member_expression property: (property_identifier) @db.model)
    ]
    property: (property_identifier) @db.operation
  )
  (#match? @db.operation "^(find|findOne|findMany|create|update|updateOne|updateMany|delete|deleteOne|deleteMany|save|aggregate)$")
)

(call_expression
  function: (member_expression
    object: (identifier) @db.connection
    property: (property_identifier) @db.operation)
  arguments: (arguments
    [
      (string (string_fragment) @db.query)
      (template_string) @db.query
    ]
  )
  (#match? @db.operation "^(query|execute)$")
)

; Mongoose model declarations
(call_expression
  function: (member_expression
    object: (identifier) @mongoose.obj (#eq? @mongoose.obj "mongoose")
    property: (property_identifier) @mongoose.prop (#eq? @mongoose.prop "model")
  )
  arguments: (arguments
    (string (string_fragment) @model.name)
  )
) @model.declaration

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

(pair
  key: (property_identifier) @function.name
  value: [
    (arrow_function)
    (function_expression)
  ]
) @function.node

(method_definition
  name: (property_identifier) @function.name
) @function.node

; standard parameters: (req, res)
[
  (function_declaration parameters: (formal_parameters (identifier) @param.name))
  (method_definition parameters: (formal_parameters (identifier) @param.name))
  (pair value: (arrow_function parameters: (formal_parameters (identifier) @param.name)))
  (variable_declarator value: (arrow_function parameters: (formal_parameters (identifier) @param.name)))
]

; destructured parameters: ({ body: { userId } }, res)
(formal_parameters
  (object_pattern) @param.destructured
)

; =============================================================================
; 6. CALLS, ARGUMENTS & CORE LOGIC
; =============================================================================

(call_expression
  function: [
    (identifier) @call.func_name
    (member_expression
      object: (_) @call.obj_name
      property: (property_identifier) @call.func_name
    )
  ]
) @call.node

(call_expression
  arguments: (arguments (_) @arg.value)
)

(new_expression
  constructor: (identifier) @call.class_name
)

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

; CommonJS: module.exports = app
(assignment_expression
  left: (member_expression
    object: (identifier) @mod (#eq? @mod "module")
    property: (property_identifier) @exp (#eq? @exp "exports")
  )
  right: (identifier) @export.name
)