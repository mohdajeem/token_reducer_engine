import os
import sys
import json
import time
from pathlib import Path

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from telemetry.live_telemetry import live_telemetry_manager
from api.mcp_server import (
    telemetry_start,
    telemetry_snapshot,
    telemetry_end,
    compare_runs
)

def test_live_telemetry_lifecycle():
    print("==================================================")
    print("Running Live Telemetry Lifecycle Verification Tests")
    print("==================================================")

    persist_dir = "snapshots/live_runs"
    os.makedirs(persist_dir, exist_ok=True)

    # 1. Test Run 1: Baseline
    print("Asserting: Starting Baseline run...")
    start_res = telemetry_start(task_name="login bug", mode="baseline")
    assert "baseline_login_bug" in start_res
    assert live_telemetry_manager.active_run is not None
    assert live_telemetry_manager.active_run["mode"] == "baseline"

    # Record some events
    print("Asserting: Recording baseline events...")
    live_telemetry_manager.record_event("user_tokens", 15229, {"files_opened": ["src/routes/auth.routes.js"]})
    live_telemetry_manager.record_event("planner_tokens", 5000, {"files_modified": ["src/controllers/auth.controller.js"]})
    live_telemetry_manager.record_event("file_view_tokens", 10000, {"path": "src/services/auth.service.js", "action": "open"})
    live_telemetry_manager.record_event("command_tokens", 5000, {"path": "src/controllers/auth.controller.js", "action": "write"})

    # Check snapshot
    print("Asserting: Snapshot metrics...")
    snap = telemetry_snapshot()
    assert "error" not in snap
    assert snap["total_tokens"] == 35229
    assert len(snap["files_opened"]) == 2
    assert len(snap["files_modified"]) == 1
    assert snap["category_breakdown"]["user_tokens"] == 15229

    # End run
    print("Asserting: Ending baseline run...")
    end_res = telemetry_end()
    assert "error" not in end_res
    assert end_res["total_tokens"] == 35229
    assert live_telemetry_manager.active_run is None

    # Verify run file exists
    base_file = os.path.join(persist_dir, "baseline_login_bug.json")
    assert os.path.exists(base_file), "Baseline run file was not persisted."
    with open(base_file, "r") as f:
        saved_data = json.load(f)
        assert saved_data["total_tokens"] == 35229

    # 2. Test Run 2: TokenReducer
    print("\nAsserting: Starting TokenReducer run...")
    start_res2 = telemetry_start(task_name="login bug", mode="token_reducer")
    assert "tokenreducer_login_bug" in start_res2
    assert live_telemetry_manager.active_run is not None
    assert live_telemetry_manager.active_run["mode"] == "token_reducer"

    # Record events
    print("Asserting: Recording token_reducer events...")
    live_telemetry_manager.record_event("user_tokens", 5000, {"files_opened": ["src/routes/auth.routes.js"]})
    live_telemetry_manager.record_event("planner_tokens", 2000, {})
    live_telemetry_manager.record_event("file_view_tokens", 3000, {"path": "src/services/auth.service.js", "action": "open"})
    live_telemetry_manager.record_event("command_tokens", 2843, {"path": "src/controllers/auth.controller.js", "action": "write"})

    # End run
    print("Asserting: Ending token_reducer run...")
    end_res2 = telemetry_end()
    assert end_res2["total_tokens"] == 12843

    # Verify run file exists
    exp_file = os.path.join(persist_dir, "tokenreducer_login_bug.json")
    assert os.path.exists(exp_file), "Experiment run file was not persisted."

    # 3. Test Compare Runs
    print("\nAsserting: Comparing runs...")
    comparison = compare_runs(baseline_run_id="baseline_login_bug", experiment_run_id="tokenreducer_login_bug")
    print("Comparison output:", json.dumps(comparison, indent=2))
    assert "error" not in comparison
    assert comparison["baseline_tokens"] == 35229, f"Expected 35229, got {comparison['baseline_tokens']}"
    assert comparison["experiment_tokens"] == 12843, f"Expected 12843, got {comparison['experiment_tokens']}"
    assert comparison["baseline_files"] == 2, f"Expected 2, got {comparison['baseline_files']}"
    assert comparison["experiment_files"] == 2, f"Expected 2, got {comparison['experiment_files']}"
    assert comparison["reduction_percent"] == 63.5, f"Expected 63.5, got {comparison['reduction_percent']}"
    assert "LIVE_COMPARISON_REPORT.md" in comparison["report_markdown"]
    assert "Status\n**PASS**" in comparison["report_markdown"] or "Status\n**FAIL**" in comparison["report_markdown"]

    # Verify report is written to workspace
    assert os.path.exists("LIVE_COMPARISON_REPORT.md"), "LIVE_COMPARISON_REPORT.md was not generated in workspace root."
    
    print("\n[SUCCESS] Live Telemetry tests passed successfully!")

if __name__ == "__main__":
    test_live_telemetry_lifecycle()
    sys.exit(0)
