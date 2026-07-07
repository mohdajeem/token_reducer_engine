; =============================================================================
; IMPORTS
; =============================================================================

(import_statement
  (import_clause
    (identifier) @import.name)

  (string
    (string_fragment) @import.source)
)

(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @import.name)))

  (string
    (string_fragment) @import.source)
)

(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @import.name
        alias: (identifier) @import.alias)))

  (string
    (string_fragment) @import.source)
)

(import_statement
  (import_clause
    (namespace_import
      (identifier) @import.alias))

  (string
    (string_fragment) @import.source)
)

; =============================================================================
; CORE LOGIC
; =============================================================================

(call_expression
  function: (identifier) @call.func_name
)

(call_expression
  function: (member_expression
    object: (_) @call.obj_name
    property: (property_identifier) @call.func_name)
)

(new_expression
  constructor: (identifier) @call.class_name
)

(variable_declarator
  name: (identifier) @variable.name

  value: (new_expression
    constructor: (identifier) @call.class_name)
)

; =============================================================================
; NETWORK IN
; =============================================================================

; =============================================================================
; ROUTES
; =============================================================================

; =============================================================================
; ROUTES
; Detect route declarations only.
; Semantic interpretation happens in Python AST traversal.
; =============================================================================

(call_expression
  function: (member_expression

    object: (identifier)
      @router.obj

    property: (property_identifier)
      @endpoint.served_method
  )

  arguments: (arguments
    .
    (string
      (string_fragment)
        @endpoint.served_route)
  )

  (#match?
    @endpoint.served_method
    "^(get|post|put|delete|patch|options|head)$")
)

; =============================================================================
; NETWORK OUT
; =============================================================================

(call_expression
  function: (identifier) @endpoint.called_method
  (#eq? @endpoint.called_method "fetch")

  arguments: (arguments
    (string
      (string_fragment) @endpoint.called_url))
)

(call_expression
  function: (member_expression
    object: (identifier) @call.obj_name
    property: (property_identifier) @endpoint.called_method)

  (#match? @call.obj_name "^(axios|client|api|http|request|requests)$")

  (#match? @endpoint.called_method "^(get|post|put|delete|patch|request)$")

  arguments: (arguments
    (string
      (string_fragment) @endpoint.called_url))
)

; =============================================================================
; DATABASE
; =============================================================================
(call_expression
  function: (member_expression
    object: (member_expression
      object: (_) @call.obj_name
      property: (property_identifier) @db.model)

    property: (property_identifier) @db.operation)

  (#match? @db.operation "^(find|findOne|findMany|create|update|delete|save)$")
)

; =============================================================================
; ERRORS
; =============================================================================

(throw_statement
  (new_expression
    constructor: (identifier) @error.throw)
)

(throw_statement
  (identifier) @error.throw
)

(catch_clause
  parameter: (identifier) @error.catch
)

; =============================================================================
; CONTRACTS
; =============================================================================

(class_declaration
  name: (identifier) @contract.name
)

; =============================================================================
; EXPORTS
; =============================================================================

(export_statement
  declaration: (function_declaration
    name: (identifier) @export.name)
)

(export_statement
  declaration: (class_declaration
    name: (identifier) @export.name)
)


; =============================================================================
; FUNCTION DEFINITIONS
; =============================================================================

; ----------------------------------------------------------
; function test() {}
; ----------------------------------------------------------

(function_declaration
  name: (identifier) @function.name
) @function.node


; ----------------------------------------------------------
; const test = () => {}
; ----------------------------------------------------------

(variable_declarator

  name: (identifier)
    @function.name

  value: [
    (arrow_function)
    (function_expression)
  ]
) @function.node


; ----------------------------------------------------------
; export const controller = {
;     getUsers: async () => {}
; }
; ----------------------------------------------------------

(pair

  key: (property_identifier)
    @function.name

  value: [
    (arrow_function)
    (function_expression)
  ]
) @function.node


; ----------------------------------------------------------
; class methods
; class X { test() {} }
; ----------------------------------------------------------

(method_definition

  name: (property_identifier)
    @function.name

) @function.node

; =============================================================================
; MONGOOSE QUERIES
; =============================================================================

; ----------------------------------------------------------
; User.find()
; User.findOne()
; User.create()
; User.updateOne()
; ----------------------------------------------------------

(call_expression
  function: (member_expression
    object: (identifier) @db.model
    property: (property_identifier) @db.operation)
    
  (#match? @db.operation
    "^(find|findOne|create|updateOne|updateMany|deleteOne|deleteMany|save)$")
)

; =============================================================================
; RAW SQL
; =============================================================================

; ----------------------------------------------------------
; db.query("SELECT * FROM users")
; connection.execute(...)
; ----------------------------------------------------------

(call_expression
  function: (member_expression
    object: (identifier) @db.connection
    property: (property_identifier) @db.operation)

  arguments: (arguments
    (string
      (string_fragment) @db.query)
  )

  (#match? @db.operation
    "^(query|execute)$")
)

; ======================================================
; SYMBOL ALIASES
; const svc = userService
; ======================================================

;(variable_declarator
;  name: (identifier) @alias.name
;  value: (identifier) @alias.value
;)

(variable_declarator

  name: (identifier)
    @alias.name

  value: (identifier)
    @alias.value

)


; ======================================================
; DESTRUCTURED SYMBOLS
; const { fetchUsers } = userService
; ======================================================

(variable_declarator

  name: (object_pattern

    (shorthand_property_identifier_pattern)
      @destructure.name
  )

  value: (identifier)
    @destructure.source
)



; ======================================================
; FUNCTION PARAMETERS
; function login(email)
; ======================================================

[
    (function_declaration
        name: (identifier) @function.name
        parameters: (formal_parameters
            (identifier) @param.name
        )
    )

    (method_definition
        name: (property_identifier) @function.name
        parameters: (formal_parameters
            (identifier) @param.name
        )
    )

    (pair
        key: (property_identifier) @function.name
        value: (arrow_function
            parameters: (formal_parameters
                (identifier) @param.name
            )
        )
    )
]


; ======================================================
; CALL ARGUMENTS
; fetchUsers(req.body.email)
; ======================================================

;;(call_expression

 ;   function: [
 ;       (identifier)
  ;      (member_expression)
   ; ]
;
 ;   arguments: (arguments
  ;      (_) @arg.value
   ; )
;)

; ======================================================
; CALL ARGUMENTS
; ======================================================

(call_expression
  function: [
    (identifier)
    (member_expression)
  ]

  arguments: (arguments
    [
      (identifier)
      (member_expression)
      (call_expression)
      (object)
      (array)
      (string)
      (number)
      (true)
      (false)
      (null)
    ] @arg.value
  )
) @call.node

(call_expression
  function: (member_expression
    object: (identifier) @call.obj_name
    property: (property_identifier) @call.func_name
  )
) @call.node

; ======================================================
; VARIABLE ASSIGNMENTS
; const x = req.body.email
; ======================================================

(variable_declarator

    name: (identifier)
        @assign.variable

    value: [

        (identifier)

        (call_expression)

        (member_expression)

        (string)

        (number)
    ] @assign.value
)


; ======================================================
; RETURN STATEMENTS
; return email
; ======================================================

;(return_statement

 ;   (identifier)
  ;      @return.value
;)

(return_statement
    [
      (identifier)
      (call_expression)
      (member_expression)
      (object)
      (array)
    ] @return.value
)



