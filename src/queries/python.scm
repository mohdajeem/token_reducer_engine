; =============================================================================
; IMPORTS
; =============================================================================

(import_statement
  name: (dotted_name) @import.source)

(import_statement
  name: (aliased_import
    name: (dotted_name) @import.source
    alias: (identifier) @import.alias))

(import_from_statement
  module_name: (dotted_name) @import.source
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.source

  name: (aliased_import
    name: (dotted_name) @import.name
    alias: (identifier) @import.alias))



; =============================================================================
; CORE LOGIC
; =============================================================================

(call
  function: (identifier) @call.func_name)

(call
  function: (attribute
    object: (_) @call.obj_name
    attribute: (identifier) @call.func_name))

(call
  function: (identifier) @call.class_name
  (#match? @call.class_name "^[A-Z]"))

(assignment
  left: (identifier) @variable.name

  right: (call
    function: (identifier) @call.class_name
    (#match? @call.class_name "^[A-Z]"))
)

; =============================================================================
; NETWORK IN
; =============================================================================

(decorator
  (call
    function: (attribute
      object: (_) @call.obj_name
      attribute: (identifier) @endpoint.served_method)

    arguments: (argument_list
      (string
        (string_content) @endpoint.served_route)))

  (#match? @endpoint.served_method "^(get|post|put|delete|patch|route)$")
)

; =============================================================================
; NETWORK OUT
; =============================================================================

(call
  function: (attribute
    object: (identifier) @call.obj_name
    attribute: (identifier) @endpoint.called_method)

  arguments: (argument_list
    [
      (string
        (string_content) @endpoint.called_url)
    ])

  (#match? @endpoint.called_method "^(get|post|put|delete|patch|request)$")
)

; =============================================================================
; DATABASE
; =============================================================================

(call
  function: (attribute
    object: (_) @db.model
    attribute: (identifier) @db.operation)
)

; =============================================================================
; ERRORS
; =============================================================================

(raise_statement
  (call
    function: (identifier) @error.throw)
)

(except_clause
  value: (identifier) @error.catch)

; =============================================================================
; CONTRACTS
; =============================================================================

(class_definition
  name: (identifier) @contract.name)

; =============================================================================
; EXPORTS
; =============================================================================

(function_definition
  name: (identifier) @export.name)

(class_definition
  name: (identifier) @export.name)
