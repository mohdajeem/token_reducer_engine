"""
CONTEXT_ENGINE
==============

THE MAIN VALUE of the semantic infrastructure.

Purpose:
Generate minimal AI-ready semantic payloads.

Responsibilities:
- Impacted file extraction
- Impacted function extraction
- Execution chain extraction
- Relevant import extraction
- Neighboring code extraction
- Semantic ranking
- Token-aware compression
- Relevance prioritization

Output format:
{
  "changed_function": "...",
  "impacted_functions": [...],
  "execution_chain": [...],
  "affected_routes": [...],
  "relevant_code": {...},
  "risk": "HIGH",
  "token_budget": 1800
}

This is the REAL product.
"""

from context_engine.context_extractor import ContextExtractor

__all__ = [
    "ContextExtractor",
]
