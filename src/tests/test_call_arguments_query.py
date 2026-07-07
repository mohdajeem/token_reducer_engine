from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_javascript as tsjavascript

CODE = """
userService.fetchUsers(
    safeEmail,
    req.body.password
);
"""

QUERY = r"""
(call_expression
  function: (member_expression)
  arguments: (arguments
    (identifier) @arg.value
  )
)
"""

LANGUAGE = Language(tsjavascript.language())
parser = Parser(LANGUAGE)

tree = parser.parse(bytes(CODE, "utf8"))

query = Query(LANGUAGE, QUERY)
cursor = QueryCursor(query)

matches = cursor.matches(tree.root_node)

print(matches)