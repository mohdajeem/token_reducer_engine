; =============================================================================
; 1. INCLUDES & CLASSES
; =============================================================================

(preproc_include) @import.node

(class_specifier
  name: (type_identifier) @class.name
) @class.node

(struct_specifier
  name: (type_identifier) @class.name
) @class.node

(namespace_definition
  name: (identifier) @class.name
) @class.node

; =============================================================================
; 2. FUNCTION & METHOD DEFINITIONS
; =============================================================================

(function_definition
  declarator: (function_declarator
    declarator: (identifier) @function.name
  )
) @function.node

(function_definition
  declarator: (function_declarator
    declarator: (field_identifier) @function.name
  )
) @function.node

(function_definition
  declarator: (function_declarator
    declarator: (qualified_identifier
      name: (identifier) @function.name
    )
  )
) @function.node

(parameter_declaration
  declarator: (identifier) @param.name
) @param.node

; =============================================================================
; 3. CALL SITES
; =============================================================================

(call_expression
  function: (identifier) @call.name
) @call.node

(call_expression
  function: (field_expression
    field: (field_identifier) @call.name
  )
) @call.node

(call_expression
  function: (qualified_identifier
    name: (identifier) @call.name
  )
) @call.node
