"""
API
===

AI Agent Integration Layer.

THIS IS VERY IMPORTANT.

Expose: REAL semantic APIs.

Endpoints:
- POST /impact
- POST /context
- POST /validate
- POST /rebuild

Example request:
{
  "file": "auth.js",
  "line": 42
}

Example response:
{
  "impacted_functions": [...],
  "affected_routes": [...],
  "semantic_context": {...}
}

This is how:
Copilot,
Cursor,
Claude,
Cline,
and other agents
consume the engine.

This becomes:
the semantic intelligence layer.
"""

__all__ = []
