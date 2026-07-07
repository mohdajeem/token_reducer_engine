# ==========================================================
# FILE:
# src/language_config.py
# ==========================================================

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs

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
    "build"
}



import os

BASE_DIR = os.path.dirname(__file__)

JS_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "javascript.scm"
)

PY_QUERY_PATH = os.path.join(
    BASE_DIR,
    "queries",
    "python.scm"
)

with open(JS_QUERY_PATH, "r") as f:
    JS_MASTER_QUERY = f.read()

with open(PY_QUERY_PATH, "r") as f:
    PY_MASTER_QUERY = f.read()




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

    ".py": {
        "LANGUAGE": Language(
            tspython.language()
        ),

        "FUNCTION_NODES": [
            "function_definition"
        ],

        "MASTER_QUERY": PY_MASTER_QUERY
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