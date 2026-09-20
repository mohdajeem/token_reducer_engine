; =============================================================================
; 1. IMPORTS & STRUCTS
; =============================================================================

(use_declaration) @import.node

(struct_item
  name: (type_identifier) @class.name
) @class.node

(enum_item
  name: (type_identifier) @class.name
) @class.node

; =============================================================================
; 2. FUNCTION & METHOD DEFINITIONS
; =============================================================================

(function_item
  name: (identifier) @function.name
) @function.node

(parameter
  pattern: (identifier) @param.name
) @param.node

; =============================================================================
; 3. CALL SITES & MACROS
; =============================================================================

(call_expression
  function: (identifier) @call.name
) @call.node

(call_expression
  function: (field_expression
    field: (field_identifier) @call.name
  )
) @call.node

(macro_invocation
  macro: (identifier) @call.name
) @call.node
