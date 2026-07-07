"""
SEMANTIC_CORE
=============

The heart of the semantic context engine.

Responsibilities:
- Tree-Sitter parsing
- Multi-pass symbol resolution
- Execution edges
- Cross-file resolution
- Graph building

This is the moat. Protect this heavily.
"""

from semantic_core.symbol_table import SymbolTable
from semantic_core.function_index import FunctionIndex
from semantic_core.graph_builder import GraphBuilder

__all__ = [
    "SymbolTable",
    "FunctionIndex",
    "GraphBuilder",
]
