#!/usr/bin/env python3
"""
SEMANTIC MATCH EXTRACTOR - FIXED VERSION
This version fixes Unicode errors and properly extracts matches.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from language_config import LanguageManager
from semantic_core.semantic_match import SemanticMatch
from semantic_core.match_classifier import classify_match
from tree_sitter import QueryCursor
from config.debug_flags import DEBUG_GRAPH_BUILD
from utils.logger import logger


_CLASS_NODE_TYPES = {"class_declaration", "class", "class_expression", "abstract_class_declaration"}
_NOT_A_CLASS = {"module", "exports", "window", "global", "globalThis", "self", "this", "document", "process", "console"}


def _text(node):
    try:
        return node.text.decode("utf-8") if isinstance(node.text, bytes) else str(node.text)
    except Exception:
        return ""


def _prototype_owner(member_node):
    """`X.prototype` member_expression -> 'X' (or 'A.B' for `A.B.prototype`), else None."""
    if member_node is None or member_node.type != "member_expression":
        return None
    prop = member_node.child_by_field_name("property")
    obj = member_node.child_by_field_name("object")
    if prop is not None and _text(prop) == "prototype" and obj is not None:
        # `p5.RendererGL.prototype.x` -> class RendererGL: the namespace prefix is dropped so
        # the class name matches what `new p5.RendererGL()` / `@param {p5.RendererGL}` yield
        return _text(obj).split(".")[-1]
    return None


def _class_name_of(class_node):
    name = class_node.child_by_field_name("name")
    if name is not None:
        return _text(name)
    # `const Foo = class { ... }` -- class_expression named by the declarator
    par = class_node.parent
    if par is not None and par.type == "variable_declarator":
        n = par.child_by_field_name("name")
        return _text(n) if n is not None else None
    return None


def _superclass_of(class_node):
    for ch in class_node.children:
        if ch.type == "class_heritage":
            for sub in ch.children:
                if sub.type in ("identifier", "member_expression", "type_identifier"):
                    return _text(sub)
            # TS: `extends X` sits inside an extends_clause
            for sub in ch.named_children:
                for leaf in (sub.named_children or [sub]):
                    if leaf.type in ("identifier", "member_expression", "type_identifier"):
                        return _text(leaf)
    return None


def find_owner_class(func_node):
    """
    The class that owns a function definition node, recovered from the AST:
      class X { m() {} }                          -> ('X', superclass)
      X.prototype.m = function () {}             -> ('X', None)
      Object.assign(X.prototype, { m() {} })     -> ('X', None)
      X.prototype = { m: function () {} }        -> ('X', None)
    Returns (class_name, superclass) or (None, None) for module-level functions.
    """
    node = func_node
    # the prototype-assignment capture IS the assignment_expression
    if node is not None and node.type == "assignment_expression":
        left = node.child_by_field_name("left")
        if left is not None and left.type == "member_expression":
            owner = _prototype_owner(left.child_by_field_name("object"))
            if owner:
                return owner, None
            # `p5.foo = function () {}` -- a static member of namespace/class p5
            obj = left.child_by_field_name("object")
            if obj is not None and obj.type == "identifier" and _text(obj) not in _NOT_A_CLASS:
                return _text(obj), None
    depth = 0
    while node is not None and depth < 12:
        par = node.parent
        if par is None:
            break
        if par.type == "class_body" and par.parent is not None and par.parent.type in _CLASS_NODE_TYPES:
            return _class_name_of(par.parent), _superclass_of(par.parent)
        # Python: function_definition [-> decorated_definition] -> block -> class_definition
        if par.type == "block" and par.parent is not None and par.parent.type == "class_definition":
            cls = par.parent
            name = cls.child_by_field_name("name")
            sup = None
            bases = cls.child_by_field_name("superclasses")
            if bases is not None:
                for ch in bases.named_children:
                    if ch.type in ("identifier", "attribute"):
                        sup = _text(ch).split(".")[-1]
                        break
            return (_text(name) if name is not None else None), sup
        if par.type == "decorated_definition":
            node = par
            depth += 1
            continue
        if par.type in _CLASS_NODE_TYPES:
            return _class_name_of(par), _superclass_of(par)
        if par.type == "object":
            gp = par.parent
            # Object.assign(X.prototype, { ... })
            if gp is not None and gp.type == "arguments" and gp.parent is not None and gp.parent.type == "call_expression":
                call = gp.parent
                fn = call.child_by_field_name("function")
                if fn is not None and _text(fn) in ("Object.assign", "_.extend", "extend", "$.extend"):
                    args = list(gp.named_children)
                    if args:
                        owner = _prototype_owner(args[0])
                        if owner:
                            return owner, None
            # X.prototype = { ... }
            if gp is not None and gp.type == "assignment_expression":
                owner = _prototype_owner(gp.child_by_field_name("left"))
                if owner:
                    return owner, None
        if par.type in ("program", "module"):
            break
        if par.type in ("function_declaration", "function_expression", "arrow_function", "method_definition", "function_definition"):
            # nested inside another function: no class ownership of its own
            return None, None
        node = par
        depth += 1
    return None, None


def _define_property_member(func_node):
    """`Object.defineProperties(X, { name: { value: fn } })` and
    `Object.defineProperty(X, 'name', { value: fn })` attach `name` to X (static when X is
    the class itself, instance when X.prototype). Chart.js defines Chart.register /
    Chart.getChart this way. Returns (name, class, is_static) or None."""
    pair = func_node if func_node is not None and func_node.type == "pair" else (func_node.parent if func_node is not None else None)
    if pair is None or pair.type != "pair":
        return None
    key = pair.child_by_field_name("key")
    if key is None or _text(key) not in ("value", "get", "set"):
        return None
    desc = pair.parent  # the descriptor object { enumerable, value: fn }
    if desc is None or desc.type != "object":
        return None
    holder = desc.parent
    name = None
    if holder is not None and holder.type == "pair":  # defineProperties: name: { value }
        k = holder.child_by_field_name("key")
        name = _text(k) if k is not None else None
        props = holder.parent
        args = props.parent if props is not None and props.type == "object" else None
    else:  # defineProperty: 'name', { value }
        args = holder
    if args is None or args.type != "arguments" or args.parent is None or args.parent.type != "call_expression":
        return None
    fn = args.parent.child_by_field_name("function")
    callee = _text(fn) if fn is not None else ""
    named = list(args.named_children)
    if callee == "Object.defineProperty" and len(named) >= 3 and named[1].type == "string":
        frag = [c for c in named[1].children if c.type == "string_fragment"]
        name = _text(frag[0]) if frag else None
    elif callee != "Object.defineProperties":
        return None
    if not name or not named:
        return None
    target = named[0]
    owner = _prototype_owner(target)
    if owner:
        return name, owner, False
    if target.type == "identifier" and _text(target) not in _NOT_A_CLASS:
        return name, _text(target), True
    return None


import re as _re

_JSDOC_PARAM_RE = _re.compile(r"@param\s*\{\s*([?!]?)([A-Za-z_$][\w$.]*)(?:<[^}]*>)?(\[\])?\s*[=]?\s*\}\s*\[?([A-Za-z_$][\w$]*)")
_STATEMENT_WRAPPERS = {"export_statement", "lexical_declaration", "variable_declaration", "expression_statement",
                       "assignment_expression", "variable_declarator", "pair", "public_field_definition"}
_PRIMITIVES = {"number", "string", "boolean", "object", "function", "any", "void", "null", "undefined",
               "array", "promise", "symbol", "bigint", "never", "unknown", "date", "regexp", "error", "element"}


def _doc_comment_before(func_node):
    """The `/** ... */` comment attached to a function: the previous sibling of the
    statement that wraps it (export / const / expression / class member)."""
    node = func_node
    for _ in range(4):
        par = node.parent
        if par is not None and par.type in _STATEMENT_WRAPPERS:
            node = par
        else:
            break
    prev = node.prev_named_sibling
    if prev is not None and prev.type == "comment":
        txt = _text(prev)
        if txt.startswith("/**"):
            return txt
    return None


def _jsdoc_param_types(comment):
    out = {}
    for m in _JSDOC_PARAM_RE.finditer(comment or ""):
        typ, is_array, name = m.group(2), m.group(3), m.group(4)
        if is_array or typ.lower() in _PRIMITIVES:
            continue
        out[name] = typ.split(".")[-1]
    return out


_TYPE_NAME_RE = _re.compile(r"[A-Z][A-Za-z0-9_]*")


def _py_annotation_type(type_node):
    """`Gear`, `"parts.Gear"`, `Optional[Gear]`, `list[Gear]` -> "Gear" (first class-like name)."""
    txt = _text(type_node).strip().strip("'\"")
    for m in _TYPE_NAME_RE.finditer(txt):
        name = m.group(0)
        if name.lower() not in _PRIMITIVES and name not in ("Optional", "Union", "List", "Dict", "Tuple", "Set", "Any",
                                                               "Callable", "Iterable", "Iterator", "Sequence", "Mapping", "Type"):
            return name
    return None


def _ts_param_types(func_node):
    """`(svc: Engine, n: number)` -> {"svc": "Engine"} from TS type annotations; Python
    `(gear: Gear, n: int = 0)` -> {"gear": "Gear"} from annotations."""
    out = {}
    params = func_node.child_by_field_name("parameters")
    if params is not None and params.type == "parameters":  # Python
        for prm in params.named_children:
            if prm.type in ("typed_parameter", "typed_default_parameter"):
                ann = prm.child_by_field_name("type")
                ident = prm.child_by_field_name("name") if prm.type == "typed_default_parameter" else next((c for c in prm.named_children if c.type == "identifier"), None)
                if ann is not None and ident is not None:
                    t = _py_annotation_type(ann)
                    if t:
                        out[_text(ident)] = t
        return out
    if params is None:
        for ch in func_node.children:
            if ch.type == "formal_parameters":
                params = ch
                break
    if params is None:
        return out
    for prm in params.named_children:
        if prm.type not in ("required_parameter", "optional_parameter"):
            continue
        pat = prm.child_by_field_name("pattern")
        ann = prm.child_by_field_name("type")
        if pat is None or ann is None or pat.type != "identifier":
            continue
        for t in ann.named_children:
            if t.type == "type_identifier":
                name = _text(t)
                if name.lower() not in _PRIMITIVES:
                    out[_text(pat)] = name
            elif t.type == "generic_type":
                base = t.child_by_field_name("name") or (t.named_children[0] if t.named_children else None)
                if base is not None and _text(base).lower() not in _PRIMITIVES:
                    out[_text(pat)] = _text(base)
    return out


def _function_body(func_node):
    if func_node.type == "assignment_expression":
        right = func_node.child_by_field_name("right")
        return right.child_by_field_name("body") if right is not None else None
    if func_node.type in ("variable_declarator", "pair"):
        val = func_node.child_by_field_name("value")
        return val.child_by_field_name("body") if val is not None else None
    if func_node.type == "call_expression":  # test callback
        return None
    return func_node.child_by_field_name("body")


_OPTIONS_OBJ_RE = _re.compile(r"(^|\.)(options?|opts|config|configuration|settings|defaults|props|params)$")


def _first_new_expression(node, depth=0):
    """Constructor name of the first `new X(...)` in an expression subtree (shallow)."""
    if node is None or depth > 4:
        return None
    if node.type == "new_expression":
        ctor = node.child_by_field_name("constructor")
        return _text(ctor).split(".")[-1] if ctor is not None else None
    if node.type == "call":  # Python: `parts.Cache()` -- a capitalised callee is a constructor
        fn = node.child_by_field_name("function")
        if fn is not None:
            name = _text(fn).split(".")[-1]
            if name[:1].isupper():
                return name
        return None
    if node.type in ("arrow_function", "function_expression", "call_expression"):
        return None
    for ch in node.named_children:
        r = _first_new_expression(ch, depth + 1)
        if r:
            return r
    return None


def _this_field_assignments(func_node, param_types):
    """`this.x = new Y()` -> {"x": "Y"}; `this.x = param` -> param's declared type, if any."""
    out = {}
    body = _function_body(func_node)
    if body is None:
        return out
    stack = [body]
    while stack:
        node = stack.pop()
        if node.type in ("assignment_expression", "assignment"):
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and right is not None and left.type in ("member_expression", "attribute"):
                obj = left.child_by_field_name("object")
                prop = left.child_by_field_name("property") or left.child_by_field_name("attribute")
                if obj is not None and prop is not None and _text(obj) in ("this", "self"):
                    field = _text(prop)
                    if right.type == "identifier" and _text(right) in param_types:
                        out[field] = param_types[_text(right)]
                    elif right.type == "member_expression" and _OPTIONS_OBJ_RE.search(_text(right.child_by_field_name("object") or right) or ""):
                        # `this.tokenizer = options.tokenizer`: the type comes from wherever the
                        # defaults object assigns `tokenizer: new Tokenizer()`; resolved late
                        # via the builder's option_defaults index
                        key = right.child_by_field_name("property")
                        if key is not None:
                            out[field] = "option:" + _text(key)
                    else:
                        # `new X()` directly, or inside `a || new X()` / `cond ? new X() : y`
                        ctor = _first_new_expression(right)
                        if ctor:
                            out[field] = ctor
        # do not descend into nested functions/classes: their `this` is a different object
        if node.type in ("function_expression", "function_declaration", "class_body", "function_definition", "class_definition") and node is not body:
            continue
        stack.extend(node.children)
    return out


def _is_static_method(fnode):
    """JS: `static m() {}`; Python: a def decorated with @staticmethod / @classmethod."""
    if fnode.type == "method_definition":
        return any(ch.type == "static" or _text(ch) == "static" for ch in fnode.children if not ch.is_named or ch.type == "static")
    if fnode.type == "function_definition" and fnode.parent is not None and fnode.parent.type == "decorated_definition":
        for ch in fnode.parent.children:
            if ch.type == "decorator" and _text(ch).strip("@ ") in ("staticmethod", "classmethod"):
                return True
    return False


def _is_pytest_fixture(fnode):
    """A def decorated with @pytest.fixture / @fixture / @pytest.fixture(scope=...).
    Returns False, True, or the injected name when the decorator says name="...". """
    if fnode.type != "function_definition" or fnode.parent is None or fnode.parent.type != "decorated_definition":
        return False
    for ch in fnode.parent.children:
        if ch.type == "decorator":
            full = _text(ch).strip("@ ")
            t = full.split("(")[0].strip()
            if t in ("fixture", "pytest.fixture", "pytest_asyncio.fixture") or t.endswith(".fixture"):
                m = _re.search(r"""name\s*=\s*['"]([A-Za-z_]\w*)['"]""", full)
                return m.group(1) if m else True
    return False


def parse_reexport(export_node):
    """
    export_statement with a source -> {"source": str, "star": bool, "names": [(exported, original)]}
      export * from './core'            -> star
      export { a, b as c } from './x'   -> names [(a, a), (c, b)]
    """
    if export_node is None or export_node.type != "export_statement":
        return None
    src = export_node.child_by_field_name("source")
    if src is None:
        return None
    source = _text(src).strip("'\"`")
    star = any(ch.type == "*" for ch in export_node.children)
    names = []
    for ch in export_node.named_children:
        if ch.type == "export_clause":
            for spec in ch.named_children:
                if spec.type != "export_specifier":
                    continue
                name = spec.child_by_field_name("name")
                alias = spec.child_by_field_name("alias")
                if name is not None:
                    names.append((_text(alias) if alias is not None else _text(name), _text(name)))
        elif ch.type == "namespace_export":
            star = True
    return {"source": source, "star": bool(star and not names), "names": names}

def normalize_route_arguments(nodes, served_method_node=None):
    call_node = None
    if served_method_node:
        current = served_method_node
        while current:
            if current.type == 'call_expression':
                call_node = current
                break
            current = current.parent
            
    if not call_node:
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
        arguments_child = None
        for child in call_node.children:
            if child.type == 'arguments':
                arguments_child = child
                break
        
        if arguments_child:
            arguments = []
            for child in arguments_child.named_children:
                #print(child.type,"|",child)
                if not child.type == 'string':
                    arguments.append(child.text.decode("utf-8"))

            if arguments:
                #print("arguments extracted in normalize_route_arguments:",arguments)
                return arguments
    
    return None


def normalize_call_expression(nodes):
    call_node = None

    for node in nodes:
        current = node

        while current:
            # `new X()` is the call only for its own constructor capture; an argument
            # `wrap(new X())` still belongs to wrap(...)
            if current.type == "call_expression" or (
                    current.type == "new_expression" and current.child_by_field_name("constructor") == node):
                call_node = current
                break

            current = current.parent

        if call_node:
            break

    if call_node:
        return {
            "call.start": call_node.start_byte,
            "call.end": call_node.end_byte
        }

    return None

def safe_extract_semantic_matches(matches, file_path, tree):
    """
    Extracts and classifies raw Tree-sitter query match captures into strongly-typed 
    SemanticMatch blocks while checking ranges to drop duplicate CALL matches.
    
    Args:
        matches (List[Tuple]): List of raw match capture IDs and node maps returned by Tree-sitter.
        file_path (str): The absolute path of the parsed source file.
        tree (Tree): The Tree-sitter parsed AST tree object.
        
    Returns:
        List[SemanticMatch]: A list of clean, scope-resolved SemanticMatch objects.
    """
    semantic_matches = []
    seen_calls = set()
    
    if not matches:
        return semantic_matches
    
    try:
        for idx, (match_id, match_dict) in enumerate(matches):
            try:
                capture_dict = {}
                raw_nodes = []
                
                # Extract captures
                served_method_node = None
                for capture_name, nodes in match_dict.items():
                    if not isinstance(nodes, list):
                        nodes = [nodes]
                    
                    extracted = []
                    for node in nodes:
                        raw_nodes.append(node)
                        if capture_name == "endpoint.served_method":
                            served_method_node = node
                        try:
                            text = node.text.decode("utf-8") if isinstance(node.text, bytes) else str(node.text)
                        except:
                            text = ""
                        extracted.append(text)
                    
                    if len(extracted) == 1:
                        capture_dict[capture_name] = extracted[0]
                    else:
                        capture_dict[capture_name] = extracted
                
                # Classify match
                ##print("\nMATCH RAW")
                ##print(capture_dict)
                match_type = classify_match(capture_dict.keys())
                

                if not raw_nodes:
                    continue
                
                # Create semantic match
                identity_node = raw_nodes[0]
                arguments = normalize_route_arguments(raw_nodes, served_method_node)
                # if arguments:
                #     capture_dict["route.arguments"] = arguments
                if(match_type == "ROUTE"):
                    ##print("match_type is route")
                    arguments = normalize_route_arguments(raw_nodes, served_method_node)
                    if arguments:
                        capture_dict["route.arguments"] = arguments
                
                if match_type == "CALL":

                    call_info = normalize_call_expression(raw_nodes)

                    if call_info:

                        capture_dict["call.start"] = (
                            call_info["call.start"]
                        )

                        capture_dict["call.end"] = (
                            call_info["call.end"]
                        )
                    
                    call_key = (
                        capture_dict.get("call.start", identity_node.start_byte),
                        capture_dict.get("call.end", identity_node.end_byte)
                    )
                    if call_key in seen_calls:
                        logger.debug("[DEDUPLICATE CALL] dropped duplicate CALL match for %s at %s", capture_dict.get("call.func_name"), call_key)
                        continue
                    seen_calls.add(call_key)

                # if match_type == "CALL_ARGUMENTS":
                    ##print("\nFOUND CALL ARG")
                    ##print(capture_dict)

                if match_type == "CALL_ARGUMENTS":

                    call_info = normalize_call_expression(raw_nodes)

                    if call_info:

                        capture_dict["call.start"] = (
                            call_info["call.start"]
                        )

                        capture_dict["call.end"] = (
                            call_info["call.end"]
                        )
                
                # # #print("raw_nodes:\n",raw_nodes)
                # #print("INSIDE MATCH EXTRACTOR FIXED(identity_node):\n",identity_node)
                
                # #print("\nINSIDE MATCH EXTRACTOR FIXED:")

                #print("CAPTURE_DICT\n:",capture_dict)

                if DEBUG_GRAPH_BUILD and match_type in {"CALL", "CALL_ARGUMENTS", "RETURN_VALUE", "FUNCTION_PARAMS"}:
                    from pathlib import Path
                    print(f"🔍 [EXTRACTED {match_type}] File: {Path(file_path).name}, Range: {identity_node.start_byte}-{identity_node.end_byte}, captures: {capture_dict}")

                if match_type == "REEXPORT":
                    rnode = match_dict.get("reexport.node")
                    rnode = rnode[0] if isinstance(rnode, list) else rnode
                    rx = parse_reexport(rnode)
                    if not rx:
                        continue
                    capture_dict["reexport.source"] = rx["source"]
                    capture_dict["reexport.star"] = rx["star"]
                    capture_dict["reexport.names"] = rx["names"]

                if match_type == "VARIABLE_ASSIGNMENT":
                    # `CHECKER_CLASS = VariablesChecker` directly in a class body: a class
                    # attribute, owned by the class (pylint's test cases inject checkers this way)
                    par = identity_node.parent
                    hops = 0
                    while par is not None and hops < 4:
                        if par.type in ("class_body", "block") and par.parent is not None and par.parent.type in ("class_definition", "class_declaration", "class"):
                            capture_dict["assign.class"] = _class_name_of(par.parent)
                            break
                        if par.type in ("function_definition", "function_declaration", "method_definition", "arrow_function", "function_expression"):
                            break
                        par = par.parent
                        hops += 1

                if match_type == "FUNCTION_DEF":
                    # a def nested in another def (a factory's inner function, a fixture that
                    # yields a closure): remember the parent so return typing can see through it
                    fnode0 = match_dict.get("function.node")
                    fnode0 = fnode0[0] if isinstance(fnode0, list) else fnode0
                    par = fnode0.parent if fnode0 is not None else None
                    while par is not None:
                        if par.type in ("function_definition",):
                            nm = par.child_by_field_name("name")
                            if nm is not None:
                                capture_dict["function.parent"] = _text(nm)
                            break
                        if par.type in ("class_definition", "module", "program"):
                            break
                        par = par.parent

                if match_type == "CLASS_DEF":
                    cnode = match_dict.get("class.node")
                    cnode = cnode[0] if isinstance(cnode, list) else cnode
                    if cnode is not None:
                        sup = _superclass_of(cnode)
                        if sup:
                            capture_dict["class.superclass"] = sup.split(".")[-1]
                    capture_dict.pop("class.heritage", None)

                if match_type == "FUNCTION_DEF":
                    fnode = match_dict.get("function.node")
                    fnode = fnode[0] if isinstance(fnode, list) else fnode
                    cls, sup = find_owner_class(fnode) if fnode is not None else (None, None)
                    dp = _define_property_member(fnode) if fnode is not None and fnode.type == "pair" else None
                    if dp:
                        # the pair capture named it `value`; it is really X.<name>
                        capture_dict["function.name"], cls, sup = dp[0], dp[1], None
                        if dp[2]:
                            capture_dict["function.static"] = True
                    if cls:
                        capture_dict["function.class"] = cls
                    if sup:
                        capture_dict["function.superclass"] = sup
                    if fnode is not None and _is_static_method(fnode):
                        capture_dict["function.static"] = True
                    if fnode is not None:
                        fx = _is_pytest_fixture(fnode)
                        if fx:
                            capture_dict["function.fixture"] = fx  # True, or the name= override
                    if fnode is not None:
                        # receiver types: JSDoc `@param {Engine} e`, TS `(e: Engine)`, and
                        # `this.field = new X()` / `this.field = typedParam` in the body
                        ptypes = {}
                        doc = _doc_comment_before(fnode)
                        if doc:
                            ptypes.update(_jsdoc_param_types(doc))
                        try:
                            ptypes.update(_ts_param_types(fnode if fnode.type not in ("assignment_expression", "variable_declarator", "pair")
                                                          else (fnode.child_by_field_name("right") or fnode.child_by_field_name("value") or fnode)))
                        except Exception:
                            pass
                        if ptypes:
                            capture_dict["function.param_types"] = ptypes
                        if cls:
                            ftypes = _this_field_assignments(fnode, ptypes)
                            if ftypes:
                                capture_dict["function.field_types"] = ftypes

                semantic_match = SemanticMatch(
                    match_type=match_type,
                    captures=capture_dict,
                    file_path=file_path,
                    owner_function=None,
                    scope_id="GLOBAL",
                    start_byte=identity_node.start_byte,
                    end_byte=identity_node.end_byte,
                    start_point=identity_node.start_point,
                    end_point=identity_node.end_point
                )
                # #print("semantic_match:",semantic_match)
                
                semantic_matches.append(semantic_match)
                
            except Exception as e:
                # Skip problematic matches
                pass
        
        # ==================================================
        # POST-PROCESS: ASSIGN OWNER FUNCTIONS
        # ==================================================
        function_scopes = []
        for sm in semantic_matches:
            if sm.match_type == "FUNCTION_DEF":
                func_name = sm.captures.get("function.name")
                if func_name:
                    function_scopes.append({
                        "name": func_name,
                        "class": sm.captures.get("function.class"),
                        "start": sm.start_byte,
                        "end": sm.end_byte,
                        # The SPECIFIC occurrence's own start_line -- two same-named
                        # methods (different classes, same or different files) have
                        # different byte ranges here even though "name" collides, so
                        # this is what lets a caller downstream tell them apart instead
                        # of collapsing to the ambiguous bare name alone.
                        "start_line": (sm.start_point[0] + 1) if sm.start_point else None
                    })

        # Sort by start byte so inner functions come first if we want,
        # but usually we want the most immediate parent.
        # Actually, for nested functions, the smallest range that contains the match is the right one.
        for sm in semantic_matches:
            if sm.match_type != "FUNCTION_DEF":
                best_fit = None
                best_fit_line = None
                best_fit_class = None
                best_size = float('inf')

                for scope in function_scopes:
                    if scope["start"] <= sm.start_byte and sm.end_byte <= scope["end"]:
                        size = scope["end"] - scope["start"]
                        if size < best_size:
                            best_size = size
                            best_fit = scope["name"]
                            best_fit_line = scope["start_line"]
                            best_fit_class = scope.get("class")

                if best_fit:
                    sm.owner_function = best_fit
                    sm.owner_function_line = best_fit_line
                    sm.owner_class = best_fit_class
            else:
                sm.owner_class = sm.captures.get("function.class")

        return semantic_matches
        
    except Exception as e:
        print(f"[ERROR] Extracting matches: {e}")
        return []


# For backward compatibility
extract_semantic_matches = safe_extract_semantic_matches
