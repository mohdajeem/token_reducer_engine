"""
VALIDATION
==========

Semantic safety verification.

Responsibilities:
- Unresolved symbol detection
- Route linkage validation
- Import validation
- Execution edge validation
- Taint drift detection
- Contract drift detection
- Dangerous semantic change detection

NO fake governance reporting.

Validation must operate on REAL graph state.
"""

from validation.semantic_validator import SemanticValidator
from validation.patch_validator import PatchValidator

__all__ = [
    "SemanticValidator",
    "PatchValidator",
]
