import os
import time
import json
from typing import Dict, Any, List, Literal, Optional, Set

class LiveTelemetryManager:
    def __init__(self, persist_dir: str = "snapshots/live_runs"):
        self.persist_dir = persist_dir
        self.active_run: Optional[Dict[str, Any]] = None

    def start_run(self, run_id: str, task_name: str, mode: Literal["baseline", "token_reducer"]):
        """
        Starts a live telemetry run.
        """
        self.active_run = {
            "run_id": run_id,
            "task_name": task_name,
            "mode": mode,
            "start_time": time.time(),
            "end_time": None,
            "categories": {
                "user_tokens": 0,
                "planner_tokens": 0,
                "file_view_tokens": 0,
                "search_tokens": 0,
                "mcp_tokens": 0,
                "command_tokens": 0,
                "diagnostic_tokens": 0,
                "tool_output_tokens": 0
            },
            "total_tokens": 0,
            "files_opened": set(),
            "files_modified": set(),
            "execution_time_seconds": 0.0
        }
        # Clear out file paths
        os.makedirs(self.persist_dir, exist_ok=True)

    def record_event(self, event_type: str, tokens: int, metadata: Dict[str, Any]):
        """
        Records a telemetry event and updates run token counts and files.
        """
        if not self.active_run:
            return

        # Increment tokens in category
        if event_type in self.active_run["categories"]:
            self.active_run["categories"][event_type] += tokens
        else:
            # Fallback if category name is slightly different
            self.active_run["categories"]["tool_output_tokens"] += tokens

        # Update total tokens
        self.active_run["total_tokens"] = sum(self.active_run["categories"].values())

        # Extract file paths opened/modified from metadata
        def extract_paths(val) -> List[str]:
            if isinstance(val, list):
                return [str(item) for item in val if item]
            elif isinstance(val, str):
                return [val]
            return []

        # 1. Check explicit metadata lists/strings
        opened_list = extract_paths(metadata.get("files_opened") or metadata.get("opened_file"))
        modified_list = extract_paths(metadata.get("files_modified") or metadata.get("modified_file"))

        for p in opened_list:
            self.active_run["files_opened"].add(p)
        for p in modified_list:
            self.active_run["files_modified"].add(p)

        # 2. Check standard paths in metadata and classify based on event/action
        path = metadata.get("path") or metadata.get("file") or metadata.get("TargetFile") or metadata.get("AbsolutePath")
        if path and isinstance(path, str):
            action = metadata.get("action", "").lower()
            if event_type == "file_view_tokens" or action == "open" or "view" in action:
                self.active_run["files_opened"].add(path)
            elif action in ["write", "modify", "replace", "delete"] or "write" in event_type or "replace" in event_type:
                self.active_run["files_modified"].add(path)
            else:
                # Default fallback
                self.active_run["files_opened"].add(path)

    def snapshot(self) -> Dict[str, Any]:
        """
        Saves the current active run state as a snapshot JSON file.
        """
        if not self.active_run:
            raise ValueError("No active run to snapshot.")

        # Compute elapsed time
        elapsed = time.time() - self.active_run["start_time"]
        self.active_run["execution_time_seconds"] = round(elapsed, 2)
        self.active_run["total_tokens"] = sum(self.active_run["categories"].values())

        # Prepare serialization dict
        serial_run = {
            "run_id": self.active_run["run_id"],
            "task_name": self.active_run["task_name"],
            "mode": self.active_run["mode"],
            "start_time": self.active_run["start_time"],
            "end_time": self.active_run["end_time"],
            "categories": self.active_run["categories"].copy(),
            "total_tokens": self.active_run["total_tokens"],
            "files_opened": sorted(list(self.active_run["files_opened"])),
            "files_modified": sorted(list(self.active_run["files_modified"])),
            "execution_time_seconds": self.active_run["execution_time_seconds"]
        }

        os.makedirs(self.persist_dir, exist_ok=True)
        run_file = os.path.join(self.persist_dir, f"{self.active_run['run_id']}.json")
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(serial_run, f, indent=2)

        return serial_run

    def end_run(self) -> Dict[str, Any]:
        """
        Ends the active run and saves its final snapshot.
        """
        if not self.active_run:
            raise ValueError("No active run to end.")

        self.active_run["end_time"] = time.time()
        res = self.snapshot()
        self.active_run = None
        return res

    def compare_runs(self, baseline_run_id: str, experiment_run_id: str) -> Dict[str, Any]:
        """
        Compares two runs and generates LIVE_COMPARISON_REPORT.md.
        """
        base_file = os.path.join(self.persist_dir, f"{baseline_run_id}.json")
        exp_file = os.path.join(self.persist_dir, f"{experiment_run_id}.json")

        if not os.path.exists(base_file):
            raise FileNotFoundError(f"Baseline run '{baseline_run_id}' not found at {base_file}")
        if not os.path.exists(exp_file):
            raise FileNotFoundError(f"Experiment run '{experiment_run_id}' not found at {exp_file}")

        with open(base_file, "r", encoding="utf-8") as f:
            base_run = json.load(f)
        with open(exp_file, "r", encoding="utf-8") as f:
            exp_run = json.load(f)

        baseline_tokens = base_run["total_tokens"]
        experiment_tokens = exp_run["total_tokens"]

        baseline_files = len(base_run["files_opened"])
        experiment_files = len(exp_run["files_opened"])

        time_base = base_run["execution_time_seconds"]
        time_exp = exp_run["execution_time_seconds"]

        # Reduction calculation
        if baseline_tokens > 0:
            reduction_percent = round((baseline_tokens - experiment_tokens) / baseline_tokens * 100, 1)
        else:
            reduction_percent = 0.0

        # Timing helper
        def format_time(seconds: float) -> str:
            m = int(seconds) // 60
            s = int(seconds) % 60
            if m > 0:
                return f"{m}m {s}s"
            return f"{s}s"

        status = "PASS" if experiment_tokens < baseline_tokens else "FAIL"

        report_markdown = f"""# LIVE_COMPARISON_REPORT.md

Task:
{base_run['task_name']}

## Baseline

* **Files Opened**: {baseline_files}
* **Tokens**: {baseline_tokens}
* **Time**: {format_time(time_base)}

## TokenReducer

* **Files Opened**: {experiment_files}
* **Tokens**: {experiment_tokens}
* **Time**: {format_time(time_exp)}

## Reduction

* **Files**:
{baseline_files} -> {experiment_files}

* **Tokens**:
{baseline_tokens} -> {experiment_tokens}

* **Reduction**:
{reduction_percent}%

## Status
**{status}**
"""

        # Persist report in workspace root
        with open("LIVE_COMPARISON_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report_markdown)

        return {
            "baseline_tokens": baseline_tokens,
            "experiment_tokens": experiment_tokens,
            "baseline_files": baseline_files,
            "experiment_files": experiment_files,
            "reduction_percent": reduction_percent,
            "execution_time_baseline": time_base,
            "execution_time_experiment": time_exp,
            "report_markdown": report_markdown
        }

# Global singleton
live_telemetry_manager = LiveTelemetryManager()
