# ==========================================================
# FILE:
# src/language_config.py
# ==========================================================

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs
import tree_sitter_java as tsjava
import tree_sitter_typescript as tsts
import tree_sitter_go as tsgo
import tree_sitter_rust as tsrust
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp

from tree_sitter import Language, Parser


# ==========================================================
# IGNORE DIRECTORIES
# ==========================================================

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".sandbox",
    ".semantic_cache",
    # test/ and tests/ are indexed since 2026-09 -- as a flagged partition (function
    # entries and edges carry is_test=True; default traversal hides them). A failing test
    # is the best pointer to the symbol that must change, and tests are the callers index
    # for library code.
    "docs",
    "docs_api",
    "extern"
}



import os

BASE_DIR = os.path.dirname(__file__)

JS_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "javascript.scm"
)

TS_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "typescript.scm"
)

PY_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "python.scm"
)

JAVA_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "java.scm"
)

GO_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "go.scm"
)

RUST_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "rust.scm"
)

C_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "c.scm"
)

CPP_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "cpp.scm"
)

with open(JS_QUERY_PATH, "r") as f:
    JS_MASTER_QUERY = f.read()

with open(TS_QUERY_PATH, "r") as f:
    TSX_MASTER_QUERY = f.read()

TS_MASTER_QUERY = "\n".join([line for line in TSX_MASTER_QUERY.splitlines() if not line.strip().startswith("(jsx_")])

with open(PY_QUERY_PATH, "r") as f:
    PY_MASTER_QUERY = f.read()

with open(JAVA_QUERY_PATH, "r") as f:
    JAVA_MASTER_QUERY = f.read()

with open(GO_QUERY_PATH, "r") as f:
    GO_MASTER_QUERY = f.read()

with open(RUST_QUERY_PATH, "r") as f:
    RUST_MASTER_QUERY = f.read()

with open(C_QUERY_PATH, "r") as f:
    C_MASTER_QUERY = f.read()

with open(CPP_QUERY_PATH, "r") as f:
    CPP_MASTER_QUERY = f.read()




# # ==========================================================
# # JAVASCRIPT / TYPESCRIPT MASTER QUERY
# # ==========================================================
# with open(r"project_with_semantic\trying1\src\queries\javascript.scm") as f:
#     JS_MASTER_QUERY = f.read()
# # ==========================================================
# # PYTHON MASTER QUERY
# # ==========================================================

# with open(r"project_with_semantic\trying1\src\queries\python.scm","r") as f:
#     PY_MASTER_QUERY = f.read()

# ==========================================================
# LANGUAGE CONFIG
# ==========================================================

LANG_CONFIG = {

    ".js": {
        "LANGUAGE": Language(
            tsjs.language()
        ),

        "FUNCTION_NODES": [
            "function_declaration",
            "method_definition",
            "arrow_function"
        ],

        "MASTER_QUERY": JS_MASTER_QUERY
    },

    ".jsx": {
        "LANGUAGE": Language(
            tsjs.language()
        ),

        "FUNCTION_NODES": [
            "function_declaration",
            "method_definition",
            "arrow_function"
        ],

        "MASTER_QUERY": JS_MASTER_QUERY
    },

    ".ts": {
        "LANGUAGE": Language(
            tsts.language_typescript()
        ),

        "FUNCTION_NODES": [
            "function_declaration",
            "method_definition",
            "arrow_function"
        ],

        "MASTER_QUERY": TS_MASTER_QUERY
    },

    ".tsx": {
        "LANGUAGE": Language(
            tsts.language_tsx()
        ),

        "FUNCTION_NODES": [
            "function_declaration",
            "method_definition",
            "arrow_function"
        ],

        "MASTER_QUERY": TSX_MASTER_QUERY
    },

    ".py": {
        "LANGUAGE": Language(
            tspython.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": PY_MASTER_QUERY
    },

    ".java": {
        "LANGUAGE": Language(
            tsjava.language()
        ),

        "FUNCTION_NODES": [
            "method_declaration",
            "constructor_declaration"
        ],

        "MASTER_QUERY": JAVA_MASTER_QUERY
    },

    ".go": {
        "LANGUAGE": Language(
            tsgo.language()
        ),

        "FUNCTION_NODES": [
            "function_declaration",
            "method_declaration"
        ],

        "MASTER_QUERY": GO_MASTER_QUERY
    },

    ".rs": {
        "LANGUAGE": Language(
            tsrust.language()
        ),

        "FUNCTION_NODES": [
            "function_item"
        ],

        "MASTER_QUERY": RUST_MASTER_QUERY
    },

    ".c": {
        "LANGUAGE": Language(
            tsc.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": C_MASTER_QUERY
    },

    ".h": {
        "LANGUAGE": Language(
            tsc.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": C_MASTER_QUERY
    },

    ".cpp": {
        "LANGUAGE": Language(
            tscpp.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": CPP_MASTER_QUERY
    },

    ".hpp": {
        "LANGUAGE": Language(
            tscpp.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": CPP_MASTER_QUERY
    },

    ".cc": {
        "LANGUAGE": Language(
            tscpp.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": CPP_MASTER_QUERY
    },

    ".cxx": {
        "LANGUAGE": Language(
            tscpp.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": CPP_MASTER_QUERY
    }
}


# ==========================================================
# LANGUAGE MANAGER
# ==========================================================

class LanguageManager:

    def __init__(self):

        self.parsers = {}

        for ext, config in LANG_CONFIG.items():

            language = config["LANGUAGE"]

            parser = Parser(language)

            self.parsers[ext] = parser

    # ======================================================
    # SUPPORT CHECK
    # ======================================================

    def is_supported(self, ext):

        return ext in LANG_CONFIG

    # ======================================================
    # GET PARSER
    # ======================================================

    def get_parser(self, ext):

        return self.parsers.get(ext)

    # ======================================================
    # GET MASTER QUERY
    # ======================================================

    def get_master_query(self, ext):

        return LANG_CONFIG[ext]["MASTER_QUERY"]

    # ======================================================
    # GET FUNCTION NODES
    # ======================================================

    def get_functional_node(self, ext):

        return LANG_CONFIG[ext][
            "FUNCTION_NODES"
        ]