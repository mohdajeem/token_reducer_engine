from tree_sitter import (
    Language,
    Parser,
    Query,
    QueryCursor
)

import tree_sitter_javascript as tsjavascript


# ==========================================================
# JAVASCRIPT CODE
# ==========================================================

CODE = r"""
router.post(
    '/login',
    authMiddleware,
    mymiddleware,
    authController.login
);
router.get('/users',authMiddleware, userMiddleware, userController.getUser)
"""


# ==========================================================
# TREE-SITTER QUERY
# ==========================================================

QUERY = r"""
(call_expression
  function: (member_expression
    object: (identifier) @router.obj

    property: (property_identifier)
      @endpoint.served_method)

  (#match?
    @endpoint.served_method
    "^(get|post|put|delete|patch)$")
)
"""


# ==========================================================
# CREATE LANGUAGE
# ==========================================================

LANGUAGE = Language(
    tsjavascript.language()
)


# ==========================================================
# CREATE PARSER
# ==========================================================

parser = Parser(LANGUAGE)

tree = parser.parse(
    bytes(CODE, "utf8")
)

root_node = tree.root_node


# ==========================================================
# CREATE QUERY
# ==========================================================

query = Query(
    LANGUAGE,
    QUERY
)

cursor = QueryCursor(query)


# ==========================================================
# EXECUTE QUERY
# ==========================================================

matches = cursor.matches(root_node)


# ==========================================================
# PRINT RESULTS
# ==========================================================

print("=" * 80)
print("QUERY MATCH RESULTS")
print("=" * 80)

for match_index, (pattern_index, captures) in enumerate(matches):

    print(f"\nMATCH #{match_index + 1}")
    print("-" * 80)

    # ======================================================
    # PRINT CAPTURES
    # ======================================================
    print("captures:", captures)

    for capture_name, nodes in captures.items():

        if not isinstance(nodes, list):
            nodes = [nodes]

        extracted_values = []

        for node in nodes:

            text = node.text.decode("utf-8")

            extracted_values.append(text)

        print(f"{capture_name}: {extracted_values}")

    # ======================================================
    # GET FULL CALL NODE
    # ======================================================

    call_node = None

    for capture_name, nodes in captures.items():

        if not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:

            current = node

            while current:

                if current.type == "call_expression":

                    call_node = current
                    break

                current = current.parent

            if call_node:
                break

        if call_node:
            break

    # ======================================================
    # PRINT FULL CALL
    # ======================================================

    if call_node:

        print("\nFULL CALL:")
        print("-" * 80)

        print(
            call_node.text.decode("utf-8")
        )

        # ==================================================
        # FIND ARGUMENTS NODE
        # ==================================================

        arguments_node = None

        for child in call_node.children:

            if child.type == "arguments":

                arguments_node = child
                break

        # ==================================================
        # EXTRACT ARGUMENTS
        # ==================================================

        if arguments_node:

            print("\nROUTE ARGUMENTS:")
            print("-" * 80)

            route_arguments = []

            for child in arguments_node.named_children:

                # Skip route path string
                if child.type == "string":
                    continue

                arg_text = (
                    child.text.decode("utf-8")
                )

                route_arguments.append(arg_text)

                print(
                    f"{child.type}: {arg_text}"
                )

            print("\nNORMALIZED ARGUMENTS:")
            print(route_arguments)


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)