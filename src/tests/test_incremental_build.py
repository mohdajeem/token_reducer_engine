import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from api.mcp_server import mcp_build_graph, mcp_query_context
from incremental_runtime.change_detector import ChangeDetector

def test_incremental_updates():
    project_root = current_file.parent.parent.parent
    test_microservice = os.path.abspath(os.path.join(project_root, "test_microservice"))

    print("==================================================")
    print("Testing Incremental Graph Build & Change Detection")
    print("==================================================")

    # 1. Initial build
    res1 = mcp_build_graph(test_microservice, force_rebuild=True)
    assert "Successfully compiled" in res1 or "Successfully" in res1, f"Expected build success, got: {res1}"

    # 2. Check cached build (no files changed)
    res2 = mcp_build_graph(test_microservice, force_rebuild=False)
    assert "cached graph" in res2 or "incrementally updated" in res2, f"Expected cache load/update, got: {res2}"

    # 3. Test ChangeDetector
    detector = ChangeDetector()
    changed = detector.get_changed_files(test_microservice)
    assert isinstance(changed, list), "Expected list of changed files"

    print("SUCCESS: Incremental build & change detection assertions passed!")

if __name__ == "__main__":
    try:
        test_incremental_updates()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
