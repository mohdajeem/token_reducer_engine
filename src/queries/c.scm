; =============================================================================
; 1. INCLUDES & STRUCTS
; =============================================================================

(preproc_include) @import.node

(struct_specifier
  name: (type_identifier) @class.name
) @class.node

; =============================================================================
; 2. FUNCTION DEFINITIONS
; =============================================================================

(function_definition
  declarator: (function_declarator
    declarator: (identifier) @function.name
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
