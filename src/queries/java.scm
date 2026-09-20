; =============================================================================
; 1. IMPORTS & EXPORTS
; =============================================================================

(import_declaration
  (scoped_identifier) @import.source
) @import.node

; Class names
(class_declaration
  (identifier) @class.name
) @class.node

(interface_declaration
  (identifier) @class.name
) @class.node

; =============================================================================
; 2. ROUTE DEFINITIONS (Spring Boot REST Endpoints)
; =============================================================================

(method_declaration
  (modifiers
    (annotation
      name: (identifier) @route.method
      arguments: (annotation_argument_list (string_literal) @route.path)
    )
  )
  (identifier) @route.handler
) @route.node

(method_declaration
  (modifiers
    (marker_annotation
      name: (identifier) @route.method
    )
  )
  (identifier) @route.handler
) @route.node

; =============================================================================
; 3. FUNCTION/METHOD DEFINITIONS & PARAMETERS
; =============================================================================

(method_declaration
  (identifier) @function.name
) @function.node

(constructor_declaration
  (identifier) @function.name
) @function.node

(formal_parameter
  name: (identifier) @param.name
) @param.node

; =============================================================================
; 4. VARIABLE ASSIGNMENTS & INJECTIONS (Type tracking)
; =============================================================================

; Local variable instantiation: UserService service = new UserService();
(local_variable_declaration
  type: (type_identifier) @assign.type
  (variable_declarator
    name: (identifier) @assign.variable
    value: (object_creation_expression
      type: (type_identifier) @assign.value_type
    )
  )
) @assign.node

; Generic field declaration (supports Autowired, private, public, etc.)
(field_declaration
  type: (type_identifier) @field.type
  (variable_declarator
    name: (identifier) @field.variable
  )
) @field.node

; =============================================================================
; 5. METHOD INVOCATIONS (Calls)
; =============================================================================

(method_invocation
  object: (identifier) @call.obj_name
  name: (identifier) @call.func_name
) @call.node

(method_invocation
  name: (identifier) @call.func_name
) @call.node

(method_invocation
  arguments: (argument_list
    [
      (identifier) @arg.value
      (string_literal) @arg.value
      (decimal_integer_literal) @arg.value
    ] @arg.node
  )
)
