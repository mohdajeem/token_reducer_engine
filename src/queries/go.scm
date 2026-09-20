; =============================================================================
; 1. IMPORTS & PACKAGES
; =============================================================================

(package_clause
  (package_identifier) @package.name
) @package.node

(import_declaration) @import.node

; =============================================================================
; 2. FUNCTION & METHOD DEFINITIONS
; =============================================================================

(function_declaration
  name: (identifier) @function.name
) @function.node

(method_declaration
  name: (field_identifier) @function.name
) @function.node

(parameter_declaration
  name: (identifier) @param.name
) @param.node

; =============================================================================
; 3. CALL SITES & TYPES
; =============================================================================

(call_expression
  function: (identifier) @call.name
) @call.node

(call_expression
  function: (selector_expression
    field: (field_identifier) @call.name
  )
) @call.node

(type_spec
  name: (type_identifier) @type.name
) @type.node
