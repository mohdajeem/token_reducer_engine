; =============================================================================
; 1. IMPORTS
; =============================================================================

(import_statement
  name: (dotted_name) @import.source)

(import_statement
  name: (aliased_import
    name: (dotted_name) @import.source
    alias: (identifier) @import.alias))

(import_from_statement
  module_name: (dotted_name) @import.source
  (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.source
  (aliased_import
    name: (dotted_name) @import.name
    alias: (identifier) @import.alias))

; `from x import *`: everything x defines (or re-exports) is visible here
(import_from_statement
  module_name: [(dotted_name) (relative_import)] @import.source
  (wildcard_import) @import.star)

; Relative imports support
(import_from_statement
  module_name: (relative_import) @import.source
  (dotted_name) @import.name)

(import_from_statement
  module_name: (relative_import) @import.source
  (aliased_import
    name: (dotted_name) @import.name
    alias: (identifier) @import.alias))

; =============================================================================
; 2. FUNCTION DEFINITIONS & PARAMETERS
; =============================================================================

(function_definition
  name: (identifier) @function.name
) @function.node

; Positional parameters
(parameters (identifier) @param.name)

; Default parameters: def foo(a=1)
(parameters
  (default_parameter
    name: (identifier) @param.name
    value: (_) @param.default
  )
)

; Typed parameters: def foo(a: int)
(parameters
  (typed_parameter
    (identifier) @param.name
    type: (_) @param.type
  )
)

; Typed default parameters: def foo(a: int = 1)
(parameters
  (typed_default_parameter
    name: (identifier) @param.name
    type: (_) @param.type
    value: (_) @param.default
  )
)

; Rest positional arguments (*args)
(parameters
  (list_splat_pattern
    (identifier) @param.star_args
  )
)

; Rest keyword arguments (**kwargs)
(parameters
  (dictionary_splat_pattern
    (identifier) @param.kw_args
  )
)

; =============================================================================
; 3. CALLS & ARGUMENTS
; =============================================================================

(call
  function: (identifier) @call.func_name)

; `_ops[op](a, b)` / `handlers.get(k)(x)` / `getattr(self, "visit_" + n)(node)`: the callee
; is computed; the builder links every plausible target, flagged dispatch / dynamic
(call
  function: (subscript) @call.dispatch)
(call
  function: (call) @call.dispatch)

(call
  function: (attribute
    object: (_) @call.obj_name
    attribute: (identifier) @call.func_name))

; Implicit protocol calls -- no call syntax, but a method runs: `for x in obj` calls
; obj.__iter__, `obj[k]` calls __getitem__, `with obj` calls __enter__. Recorded as calls
; of the dunder on the receiver; resolved only through a KNOWN receiver type (never by
; unique-name guessing, every iterable defines __iter__).
(for_statement
  right: (_) @call.proto_iter)
(subscript
  value: (_) @call.proto_getitem)
(with_item
  value: (_) @call.proto_enter)
(call
  function: (identifier) @_len (#eq? @_len "len")
  arguments: (argument_list (_) @call.proto_len))

; `for search in (GridSearchCV(), RandomizedSearchCV()):` -- the loop target takes every
; element's type (candidates)
(for_statement
  left: (identifier) @assign.variable
  right: (_) @assign.value)

(call
  function: (identifier) @call.class_name
  (#match? @call.class_name "^[A-Z]"))

(call
  arguments: (argument_list
    [
      (keyword_argument value: (_) @arg.value)
      ((_) @arg.value (#not-parent-type? @arg.value keyword_argument))
    ]))

(assignment
  left: (identifier) @assign.variable
  right: (_) @assign.value)

; `fig, ax = plt.subplots()`: tuple targets, typed positionally from the callee's `return fig, axs`
(assignment
  left: [(pattern_list) (tuple_pattern)] @assign.variable
  right: (_) @assign.value)

; `self.handlers = {...}` / `self.engine = Engine()`: field assignments are variable states
; too (dispatch tables live on instances; `self.x.m()` can be typed from them)
(assignment
  left: (attribute) @assign.variable
  right: (_) @assign.value
  (#match? @assign.variable "^self\."))

; `with Session() as s:` binds s exactly like `s = Session()`
(with_item
  value: (as_pattern
    (_) @assign.value
    alias: (as_pattern_target (identifier) @assign.variable)))

; =============================================================================
; 4. NETWORK IN (Flask & FastAPI Decorators)
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

; Django route/url mappings
(call
  function: (identifier) @endpoint.served_method
  arguments: (argument_list
    [
      (string
        (string_content) @endpoint.served_route)
    ])
  (#match? @endpoint.served_method "^(path|re_path|url)$")
)

; =============================================================================
; 5. NETWORK OUT & TAINT SOURCES
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

(attribute
  object: (identifier) @req.obj
  attribute: (identifier) @req.prop
  (#match? @req.obj "^(request|req)$")
  (#match? @req.prop "^(args|form|json|headers|GET|POST|FILES|data)$")
) @taint.source

; =============================================================================
; 6. DATABASE & TAINT SINKS
; =============================================================================

(call
  function: (attribute
    object: (_) @db.model
    attribute: (identifier) @db.operation)
  (#match? @db.operation "^(filter|filter_by|raw|execute|add|commit|delete|get|create)$")
)

(call
  function: (identifier) @sink.func
  arguments: (argument_list (_) @taint.sink)
  (#match? @sink.func "^(eval|exec|compile)$")
)

(call
  function: (attribute
    object: (identifier) @sub.obj
    attribute: (identifier) @sub.func)
  arguments: (argument_list (_) @taint.sink)
  (#match? @sub.obj "^(subprocess|os)$")
  (#match? @sub.func "^(run|popen|system|exec|call)$")
)

; =============================================================================
; 7. ERRORS, CONTRACTS & EXPORTS
; =============================================================================

(raise_statement
  [
    (call
      function: (identifier) @error.throw)
    (identifier) @error.throw
    (attribute) @error.throw
  ]
)

(except_clause
  value: (identifier) @error.catch)

(return_statement
  (_) @return.value)

; a fixture's `yield app` is its return value for typing purposes
(yield
  (_) @return.value)

(class_definition
  name: (identifier) @contract.name
  superclasses: (argument_list . (_) @contract.superclass)?)

(function_definition
  name: (identifier) @export.name)

(class_definition
  name: (identifier) @export.name)
