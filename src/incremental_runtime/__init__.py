"""
INCREMENTAL_RUNTIME
===================

High-speed live semantic updates.

Responsibilities:
- File invalidation
- Incremental rebuild
- Graph delta updates
- Ownership updates
- Snapshot management
- In-memory graph state

NO full repo rebuilds on save.

Update only impacted semantic regions.
"""

from incremental_runtime.change_detector import ChangeDetector
from incremental_runtime.graph_invalidator import GraphInvalidator
from incremental_runtime.snapshot_manager import SnapshotManager

__all__ = [
    "ChangeDetector",
    "GraphInvalidator",
    "SnapshotManager",
]
