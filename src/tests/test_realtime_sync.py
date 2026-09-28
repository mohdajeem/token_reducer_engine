import os
import unittest
import tempfile
import time
import shutil
import threading
import sys
from pathlib import Path

# Add project root and src directories to Python Path
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(root_path / "src"))

from build_graph import build_graph
from incremental_runtime.graph_watcher import GraphWatcher
from incremental_runtime.incremental_graph_manager import IncrementalGraphManager
from semantic_core.graph_builder import GraphBuilder


class TestRealtimeSync(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, ".semantic_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.lock = threading.Lock()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_realtime_file_watcher_updates_graph(self):
        """Test that the background GraphWatcher detects file modifications and updates the graph automatically."""
        test_file = os.path.join(self.temp_dir, "app.js")
        rel_path = "app.js"

        # 1. Create initial test file
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("function originalFunc() { return 1; }\n")

        # 2. Build initial graph
        graph = build_graph(self.temp_dir)
        funcs = [fn.get("name") if isinstance(fn, dict) else fn for fn in graph["functions"].get(rel_path, [])]
        self.assertIn("originalFunc", funcs)
        self.assertNotIn("dynamicFunc", funcs)

        # 3. Setup IncrementalGraphManager and GraphWatcher
        builder = GraphBuilder()
        builder.graph = graph
        manager = IncrementalGraphManager(
            graph_builder=builder,
            match_extractor=None,
            project_root=self.temp_dir
        )
        manager.save_graph_snapshot(graph)

        
        # Start watcher with a short polling interval (0.2s)
        interval = 0.2
        watcher = GraphWatcher(
            project_root=self.temp_dir,
            incremental_graph_manager=manager,
            lock=self.lock,
            interval=interval
        )
        watcher.start()

        try:
            # Let the watcher complete a scan BEFORE the file changes. start() returns
            # immediately and the first scan is up to `interval` later; writing in that window
            # makes the watcher baseline the NEW content, leaving no change to detect at all.
            # That race, not slowness, is why this test passed once in three identical runs.
            time.sleep(interval * 3)

            # 4. Modify test file by appending a new function
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("function originalFunc() { return 1; }\nfunction dynamicFunc() { return 2; }\n")

            # 5. Wait for watcher loop to scan and process
            # Was a flat sleep(0.8). That is enough when the machine is idle and not enough
            # when the rest of the suite is running beside it, so this test failed in a full
            # run and passed on its own -- a failure that says nothing about the watcher.
            deadline = time.time() + 10.0
            while time.time() < deadline:
                with self.lock:
                    names = [fn.get("name") if isinstance(fn, dict) else fn
                             for fn in builder.graph["functions"].get(rel_path, [])]
                if "dynamicFunc" in names:
                    break
                time.sleep(0.05)

            # 6. Verify that the graph has been updated automatically in the background
            with self.lock:
                updated_funcs = [fn.get("name") if isinstance(fn, dict) else fn for fn in builder.graph["functions"].get(rel_path, [])]
            
            self.assertIn("originalFunc", updated_funcs)
            self.assertIn("dynamicFunc", updated_funcs)

        finally:
            watcher.stop()

if __name__ == "__main__":
    unittest.main()
