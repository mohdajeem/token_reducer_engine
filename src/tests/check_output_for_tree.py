from tree_sitter import Language, Parser
from tree_sitter_javascript import language


from tree_sitter import (
    Language,
    Parser,
    Query,
    QueryCursor
)

import tree_sitter_javascript as tsjavascript


# # Create parser
# parser = Parser()

# Load JavaScript language
LANGUAGE = Language(language())

parser = Parser(LANGUAGE)

# parser.language = JS_LANGUAGE

# # Your test code
# code = b"""
# axios.get("/users")

# console.log("hello")

# user.profile.name

# user.profile.ajeem.name.class
# user.profile.getName().class
# user.graph.profie(ajeem.class.name).class
# """

code = b"""
router.post(
    '/login',
    authMiddleware,
    authController.login,
    authentication
);
"""

# Parse code
tree = parser.parse(code)

# Recursive printer
def print_tree(node, code, indent=0):
    print("  " * indent + f"{node.type}: {code[node.start_byte:node.end_byte].decode()}")

    for child in node.children:
        print_tree(child, code, indent + 1)

print_tree(tree.root_node, code)






# QUERY = r"""
# (call_expression
#     function: (member_expression
#         object: (identifier) @router.obj 
#         property: (property_identifier) @router.served_method
#     )
# )
# """


# LANGUAGE = Language(tsjavascript.language())

# parser = Parser(LANGUAGE)

# query = Query(
#     LANGUAGE,
#     QUERY
# )

# cursor = QueryCursor(query)

# matches = cursor.matches(tree.root_node)

# print("-"*80)
# print("runing the query")

# for match_ind, match_dict in matches:
#     print(match_dict)
#     for key in match_dict:
#         print(key)
#         print(match_dict[key])
#         # print(match_dict[key].type)
#         nodes = match_dict[key]
#         if not isinstance(nodes, list):
#             nodes = [nodes]
        
#         print("printing_nodes...")
#         call_nodes = []
#         for node in nodes:
#             print(node)
#             if node.type == 'call_expression':
#                 call_nodes.append(node)
#             print("node type:",node.type)
#             print("node start point:",node.start_point)
#             print("node start byte:",node.start_byte)
#         print("call_nodes:",call_nodes)
#     # for ind, dict in match_dict:
#     #     print("match_ind",ind)
#     #     print("dict:",dict)

# print("="*80)

# for match_index, (pattern_index, captures) in enumerate(matches):
#     print("match_index:",match_index)
#     print("pattern_index", pattern_index)
#     print("captures:",captures)
#     print("items...")
#     for capture_name, nodes in captures.items():
#         print("capture_name:",capture_name)

#         if not isinstance(nodes, list):
#             nodes = [nodes]
#         print("printing nodes in capture")
#         extracted_values = []
#         for node in nodes:
#             text = node.text.decode("utf-8")
#             extracted_values.append(text)
#         print(f"{capture_name}: {extracted_values}")

#     # now we are going to check the call nodes
    
#     call_node = None
#     for capture_name, nodes in captures.items():
#         if not isinstance(nodes, list):
#             nodes = [nodes]
        
#         for node in nodes:
#             current = node
#             while current:
#                 if current.type == 'call_expression':
#                     # print(current)
#                     call_node = current
#                     break
#                 current = current.parent
#             if call_node:
#                 break
        
#         if call_node:
#             break

    
#     if call_node:
#         print("call_node:\n")
#         print(call_node.text.decode("utf-8"))

#         print("its child:\n")
#         arguments_child = None
#         for child in call_node.children:
#             print(child.type)
#             if child.type == 'arguments':
#                 arguments_child = child
#                 print(child)
#                 break
        
#         # printing the arguments named child
#         print("="*40)
#         if arguments_child:
#             print("argument_child:\n",arguments_child)
#             arguments = []
#             arguments_nodes = []
#             for child in arguments_child.named_children:
#                 print(child.type,"|",child)
#                 if not child.type == 'string':
#                     arguments.append(child.text.decode("utf-8"))
#                     arguments_nodes.append(child)

#         if arguments:
#             print("*"*50)
#             print("arguments:\n")
#             print(arguments)

#         if arguments_nodes:
#             print("$"*80)
#             # print(arguments_nodes)

#             for arg in arguments_nodes:
#                 print("argument node:\n",arg)

#                 for child in arg.children:
#                     print("child type:",child.type,"| child:",child)
#                     if child.type == 'identifier':
#                         print("object:",child.text.decode("utf-8"))
#                     elif child.type == 'property_identifier':
#                         print("function:", child.text.decode("utf-8"))




def get_arguments(code, tree):
    QUERY = r"""
        (call_expression
            function: (member_expression
                object: (identifier) @router.obj 
                property: (property_identifier) @router.served_method
            )
        )
        """

    query = Query(LANGUAGE, QUERY)
    cursor = QueryCursor(query)

    matches = cursor.matches(tree.root_node)

    for match_index, (pattern_index, captures) in enumerate(matches):
        # now we are going to check the call nodes
        
        call_node = None
        for capture_name, nodes in captures.items():
            if not isinstance(nodes, list):
                nodes = [nodes]
            
            for node in nodes:
                current = node
                while current:
                    if current.type == 'call_expression':
                        call_node = current
                        break
                    current = current.parent
                if call_node:
                    break
            
            if call_node:
                break

        
        if call_node:
            arguments_child = None
            for child in call_node.children:
                if child.type == 'arguments':
                    arguments_child = child
                    break
            
            # printing the arguments named child
            if arguments_child:
                arguments = []
                for child in arguments_child.named_children:
                    print(child.type,"|",child)
                    if not child.type == 'string':
                        arguments.append(child.text.decode("utf-8"))

            if arguments:
                return arguments
    return None


code = b"""
router.post(
    '/login',
    authMiddleware,
    authController.login,
    authentication
);
"""

# Parse code
tree = parser.parse(code)

# arguments = get_arguments(code=code, tree=tree)

# middlewares = arguments[:-1]
# print(middlewares)
# calling_function = arguments[-1]
# print(calling_function)



QUERY = r"""
    (call_expression
        function: (member_expression
            object: (identifier) @router.obj 
            property: (property_identifier) @router.served_method
        )
    )
"""

query = Query(LANGUAGE, QUERY)
cursor = QueryCursor(query)

matches = cursor.matches(tree.root_node)
# print(code)

for idx, (match_id, match_dict) in enumerate(matches):
    try:
        capture_dict = {}
        raw_nodes = []
        
        # Extract captures
        for capture_name, nodes in match_dict.items():
            if not isinstance(nodes, list):
                nodes = [nodes]
            print("\ncapture_name:\n",capture_name)
            print("capture_node:\n",nodes)
            extracted = []
            for node in nodes:
                raw_nodes.append(node)
                try:
                    text = node.text.decode("utf-8") if isinstance(node.text, bytes) else str(node.text)
                except:
                    text = ""
                extracted.append(text)
            
            if len(extracted) == 1:
                capture_dict[capture_name] = extracted[0]
            else:
                capture_dict[capture_name] = extracted
        
        
        if not raw_nodes:
            continue
        
        # Create semantic match
        identity_node = raw_nodes[0]
        print("raw_nodes:\n",raw_nodes)
        
        print("INSIDE MATCH EXTRACTOR FIXED:\n")

        print("CAPTURE_DICT\n:",capture_dict)

        # semantic_match = SemanticMatch(
        #     match_type=match_type,
        #     captures=capture_dict,
        #     file_path=file_path,
        #     owner_function=None,
        #     scope_id="GLOBAL",
        #     start_byte=identity_node.start_byte,
        #     end_byte=identity_node.end_byte,
        #     start_point=identity_node.start_point,
        #     end_point=identity_node.end_point
        # )
        
        # semantic_matches.append(semantic_match)
        
    except Exception as e:
        # Skip problematic matches
        pass
