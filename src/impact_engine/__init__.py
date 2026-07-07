"""
IMPACT_ENGINE
=============

Deterministic semantic impact analysis.

Responsibilities:
- Upstream traversal
- Downstream traversal
- Route impact
- Taint-aware traversal
- Dependency radius
- Semantic blast radius

This engine determines: WHAT ACTUALLY MATTERS.
"""

from impact_engine.graph_traversal import GraphTraversal
from impact_engine.taint_traversal_engine import TaintTraversalEngine
from impact_engine.traversal_policy import TraversalPolicy, PolicyTraversalEngine

__all__ = [
    "GraphTraversal",
    "TaintTraversalEngine",
    "TraversalPolicy",
    "PolicyTraversalEngine",
]
