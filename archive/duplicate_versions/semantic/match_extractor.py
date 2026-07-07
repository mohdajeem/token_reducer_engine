# from config.debug_flags import *
from config.settings import *
from semantic.semantic_match import SemanticMatch

from semantic.match_classifier import (
    classify_match
)

from tree_sitter import QueryCursor
# ==========================================================
# BUILD FUNCTION SPANS
# ==========================================================

def build_function_spans(root_node):

    spans = []

    stack = [root_node]

    while stack:

        node = stack.pop()

        # ======================================================
        # FUNCTION-TYPE NODES
        # ======================================================

        if node.type in {

            "function_declaration",

            "arrow_function",

            "function_expression",

            "method_definition"
        }:

            # print("\nFUNCTION NODE:")
            # print(node.type)
            if DEBUG_FUNCTION_SPANS:
                print("\nFUNCTION NODE:")
                print(node.type)

            try:

                if DEBUG_FUNCTION_SPANS:
                    print(
                        node.text.decode("utf-8")
                    )

            except:
                pass

            function_name = None

            # ==================================================
            # NORMAL FUNCTION DECLARATION
            # function test() {}
            # ==================================================

            if node.type == "function_declaration":

                name_node = (
                    node.child_by_field_name(
                        "name"
                    )
                )

                if name_node:

                    try:

                        function_name = (
                            name_node.text.decode(
                                "utf-8"
                            )
                        )

                    except:

                        function_name = None

            # ==================================================
            # WALK UPWARD
            # IMPORTANT:
            # Arrow functions can be wrapped in:
            # - pair
            # - variable_declarator
            # - parenthesized_expression
            # - assignment_expression
            # etc.
            #
            # We DO NOT trust direct parent only.
            # ==================================================

            current = node.parent

            while current and function_name is None:

                # ==============================================
                # VARIABLE DECLARATOR
                # const x = () => {}
                # ==============================================

                if current.type == "variable_declarator":

                    name_node = (
                        current.child_by_field_name(
                            "name"
                        )
                    )

                    if name_node:

                        try:

                            function_name = (
                                name_node.text.decode(
                                    "utf-8"
                                )
                            )

                            break

                        except:

                            pass

                # ==============================================
                # OBJECT PROPERTY
                # getUsers: async () => {}
                # ==============================================

                elif current.type == "pair":

                    key_node = (
                        current.child_by_field_name(
                            "key"
                        )
                    )

                    # ==========================================
                    # FALLBACK
                    # Some JS grammars do not expose key field
                    # ==========================================

                    if key_node is None:

                        for child in current.children:

                            if child.type in {

                                "property_identifier",

                                "identifier",

                                "property_signature"
                            }:

                                key_node = child
                                break

                    if key_node:

                        try:

                            function_name = (
                                key_node.text.decode(
                                    "utf-8"
                                )
                            )

                            break

                        except:

                            pass

                # ==============================================
                # CLASS METHODS
                # class X { test() {} }
                # ==============================================

                elif current.type == "method_definition":

                    name_node = (
                        current.child_by_field_name(
                            "name"
                        )
                    )

                    if name_node:

                        try:

                            function_name = (
                                name_node.text.decode(
                                    "utf-8"
                                )
                            )

                            break

                        except:

                            pass

                # ==============================================
                # MOVE UPWARD
                # ==============================================

                current = current.parent

            # ==================================================
            # STORE FUNCTION SPAN
            # ==================================================

            spans.append({

                "scope_id": (

                    function_name

                    if function_name

                    else "GLOBAL"
                ),

                "name": function_name,

                "start": node.start_byte,

                "end": node.end_byte
            })

        # ======================================================
        # DFS TRAVERSAL
        # ======================================================

        for child in reversed(node.children):

            stack.append(child)

    # ==========================================================
    # DEBUG
    # ==========================================================

    if DEBUG_FUNCTION_SPANS:
        print("\n🔥 FUNCTION SPANS")

    if DEBUG_FUNCTION_SPANS:
        for s in spans:
            print(s)

    return spans


# ==========================================================
# EXTRACT SEMANTIC MATCHES
# ==========================================================

def extract_semantic_matches(matches, file_path, tree):

    semantic_matches = []

    # ======================================================
    # BUILD FUNCTION SPANS
    # ======================================================

    function_spans = build_function_spans(
        tree.root_node
    )


    if DEBUG_FUNCTION_SPANS:
        print("\nFUNCTION SPANS:")


    if DEBUG_FUNCTION_SPANS:
        for span in function_spans:

            print(span)

    print("="*50)
    print("function span done...")
    print("="*50)
    # ======================================================
    # PROCESS MATCHES
    # ======================================================

    for _, match_dict in matches:

        capture_dict = {}

        raw_nodes = []

        # ==================================================
        # EXTRACT CAPTURES
        # ==================================================

        for capture_name, nodes in match_dict.items():

            if not isinstance(nodes, list):

                nodes = [nodes]

            extracted = []

            for node in nodes:

                raw_nodes.append(node)

                try:

                    text = (
                        node.text.decode(
                            "utf-8"
                        )
                    )

                except:

                    text = ""

                extracted.append(text)

            if len(extracted) == 1:

                capture_dict[
                    capture_name
                ] = extracted[0]

            else:

                capture_dict[
                    capture_name
                ] = extracted

        # ==================================================
        # CLASSIFY MATCH
        # ==================================================

        match_type = classify_match(
            capture_dict.keys()
        )

        if "destructure.name" in capture_dict:

            if DEBUG_MATCHES:
                print("\n🔥 DESTRUCTURE MATCH FOUND")
                print(capture_dict)

        if "alias.name" in capture_dict:
            if DEBUG_MATCHES:
                print("\n🔥 ALIAS MATCH FOUND")
                print(capture_dict)

        # ==================================================
        # DEFAULTS
        # ==================================================

        print("match types: ", match_type)

        owner_function = None

        scope_id = "GLOBAL"

        match_start = None

        match_end = None
        
        match_start_point = None

        match_end_point = None

        # ==================================================
        # NORMALIZE SEMANTIC IDENTITY
        # IMPORTANT:
        # Ownership MUST use normalized nodes
        # ==================================================

        if raw_nodes:

            identity_node = raw_nodes[0]

            # ======================================================
            # FUNCTION NODE OVERRIDE
            # ======================================================

            if (match_type == "FUNCTION_DEF" and "function.node" in match_dict):
                function_nodes = match_dict[
                    "function.node"
                ]
                if isinstance(function_nodes, list):
                    identity_node = function_nodes[0]
                else:
                    identity_node = function_nodes

            # ==================================================
            # CALLS + CALL ARGUMENTS
            # ==================================================

            if match_type in {

                "CALL",

                "CALL_ARGUMENTS"
            }:

                current = identity_node

                while current:

                    if current.type == "call_expression":

                        identity_node = current
                        break

                    current = current.parent

            # ==================================================
            # RETURN VALUES
            # ==================================================

            elif match_type == "RETURN_VALUE":

                current = identity_node

                while current:

                    if current.type == "return_statement":

                        identity_node = current
                        break

                    current = current.parent

            # ==================================================
            # FIND MOST SPECIFIC FUNCTION SCOPE
            # USING NORMALIZED NODE
            # ==================================================

            best_scope = None

            best_scope_size = None

            for span in function_spans:

                if (

                    identity_node.start_byte >= span["start"]

                    and

                    identity_node.end_byte <= span["end"]
                ):

                    scope_size = (
                        span["end"] - span["start"]
                    )

                    # ==========================================
                    # PICK INNERMOST FUNCTION
                    # ==========================================

                    if (

                        best_scope_size is None

                        or

                        scope_size < best_scope_size
                    ):

                        best_scope_size = scope_size

                        best_scope = span

            if best_scope:

                owner_function = (
                    best_scope["name"]
                )

                scope_id = (
                    best_scope["scope_id"]
                )

            # ==================================================
            # MATCH LOCATION
            # ==================================================

            match_start = (
                identity_node.start_byte
            )

            match_end = (
                identity_node.end_byte
            )

            match_start_point = (
                identity_node.start_point
            )

            match_end_point = (
                identity_node.end_point
            )

        # ==================================================
        # CREATE SEMANTIC MATCH
        # ==================================================

        semantic_match = SemanticMatch(

            match_type=match_type,

            captures=capture_dict,

            file_path=file_path,

            owner_function=owner_function,

            scope_id=scope_id,

            start_byte=match_start,

            end_byte=match_end,

            start_point=match_start_point,

            end_point=match_end_point
        )

        semantic_matches.append(
            semantic_match
        )

    return semantic_matches



# ==========================================================
# EXTRACT FILE
# ==========================================================

def extract_file(

    self,

    file_path
):

    from language_config import (
        LanguageManager
    )

    # from semantic.capture_processor import (
    #     process_captures
    # )

    from semantic.capture_processor import (
        CaptureProcessor
    )

    # ======================================================
    # LANGUAGE MANAGER
    # ======================================================

    language_manager = (
        LanguageManager()
    )

    # ======================================================
    # LOAD LANGUAGE
    # ======================================================

    # parser = (
    #     language_manager
    #     .get_parser_for_file(
    #         file_path
    #     )
    # )

    # query = (
    #     language_manager
    #     .get_query_for_file(
    #         file_path
    #     )
    # )

    

    # if parser is None or query is None:

    #     return []

    # ======================================================
    # FILE EXTENSION
    # ======================================================

    import os

    _, ext = os.path.splitext(
        file_path
    )

    # ======================================================
    # GET PARSER
    # ======================================================

    parser = (
        language_manager
        .get_parser(ext)
    )

    # ======================================================
    # GET QUERY
    # ======================================================

    query_string = (
        language_manager
        .get_master_query(ext)
    )

    if parser is None:
        return []

    language = (
        parser.language
    )

    query = language.query(
        query_string
    )

    # ======================================================
    # READ FILE
    # ======================================================

    with open(

        file_path,

        "r",

        encoding="utf-8"
    ) as f:

        source_code = f.read()

    # ======================================================
    # PARSE TREE
    # ======================================================

    tree = parser.parse(

        bytes(
            source_code,
            "utf-8"
        )
    )

    # ======================================================
    # QUERY MATCHES
    # ======================================================

    # matches = query.matches(
    #     tree.root_node
    # )

    # ======================================================
    # QUERY CURSOR
    # ======================================================

    # ======================================================
    # QUERY CURSOR
    # ======================================================

    cursor = QueryCursor(
        query
    )

    matches = cursor.matches(
        tree.root_node
    )

    # ======================================================
    # PROCESS CAPTURES
    # ======================================================

    # processed_matches = (
    #     process_captures(
    #         matches
    #     )
    # )

    # ======================================================
    # CAPTURE PROCESSOR
    # ======================================================

    capture_processor = (
        CaptureProcessor(None)
    )

    processed_matches = matches

    # ======================================================
    # EXTRACT SEMANTIC MATCHES
    # ======================================================

    semantic_matches = (
        extract_semantic_matches(

            processed_matches,

            file_path,

            tree
        )
    )

    return semantic_matches