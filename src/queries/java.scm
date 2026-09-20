; =============================================================================
; 1. IMPORTS & EXPORTS
; =============================================================================

; `import a.b.C;` / `import static a.b.C.m;` / `import static a.b.C.*;` / `import a.b.*;`
(import_declaration
  "static"? @import.static
  (scoped_identifier) @import.source
  (asterisk)? @import.star
) @import.node

; Class names (extends / implements are read off the node by the extractor:
; `superclass` -> class.superclass, `super_interfaces` -> class.interfaces)
(class_declaration
  name: (identifier) @class.name
) @class.node

(interface_declaration
  name: (identifier) @class.name
) @class.node

(enum_declaration
  name: (identifier) @class.name
) @class.node

(record_declaration
  name: (identifier) @class.name
) @class.node

; =============================================================================
; 2. ROUTES (Spring @GetMapping / @RequestMapping) and @Test
; =============================================================================
; Not a query rule: EVERY annotation (@Override, @Test, @Autowired) used to match here as a
; "route" and came out UNKNOWN. The extractor reads the annotations off the
; method_declaration / class_declaration node instead (function.annotations,
; class.annotations); the builder turns *Mapping ones into routes.

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

; Local variables: the DECLARED type types the variable whatever the value is --
; `Owner found = owners.findById(1);`, `Owner o = new Owner();`, `List<Pet> pets = ...;`
; (`var x = new Owner()` has type "var": the builder falls back to the value)
(local_variable_declaration
  type: (type_identifier) @assign.type
  (variable_declarator
    name: (identifier) @assign.variable
    value: (_)? @assign.value
  )
) @assign.node

(local_variable_declaration
  type: (generic_type
    . (type_identifier) @assign.type
  )
  (variable_declarator
    name: (identifier) @assign.variable
    value: (_)? @assign.value
  )
) @assign.node

; `for (Pet pet : owner.getPets())` -- the loop variable is declared with its type
(enhanced_for_statement
  type: (type_identifier) @assign.type
  name: (identifier) @assign.variable
) @assign.node

; Generic field declaration (supports Autowired, private, public, etc.)
(field_declaration
  type: (type_identifier) @field.type
  (variable_declarator
    name: (identifier) @field.variable
  )
) @field.node

; `private final Map<String, Pet> pets;` / `List<Owner> owners;` -- the raw type is the
; receiver type of `pets.get(..)`; the type arguments are kept in field.type_args
(field_declaration
  type: (generic_type
    . (type_identifier) @field.type
    (type_arguments) @field.type_args
  )
  (variable_declarator
    name: (identifier) @field.variable
  )
) @field.node

; =============================================================================
; 5. METHOD INVOCATIONS (Calls)
; =============================================================================

; the receiver is ANY expression: `owners.save(o)`, `this.owners.findById(id)`,
; `this.tick()`, `new Owner().getId()`, `mockMvc.perform(..).andExpect(..)` -- the builder
; types it (field / local / instantiation / call-return); 40% of petclinic's calls have a
; field_access or method_invocation receiver that the old `(identifier)`-only rule dropped
(method_invocation
  object: (_) @call.obj_name
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
