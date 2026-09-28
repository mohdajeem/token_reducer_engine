#!/usr/bin/env python3
"""
Unit tests for Incremental Graph Updates & Dirty File Invalidation.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path

from build_graph import build_graph
from incremental_runtime.snapshot_manager import SnapshotManager
from incremental_runtime.change_detector import ChangeDetector
from incremental_runtime.graph_invalidator import GraphInvalidator
from semantic_core.graph_builder import GraphBuilder
from semantic_core.match_extractor_fixed import safe_extract_semantic_matches
from language_config import LanguageManager

class TestIncrementalUpdates(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, ".semantic_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_incremental_file_invalidation_and_rebuild(self):
        """Test that modifying a single file invalidates only that file and re-stitches its graph."""
        file1 = os.path.join(self.temp_dir, "file1.js")
        file2 = os.path.join(self.temp_dir, "file2.js")

        with open(file1, "w", encoding="utf-8") as f:
            f.write("function initialFunc() { return 42; }\n")

        with open(file2, "w", encoding="utf-8") as f:
            f.write("function untouchedFunc() { return 100; }\n")

        # 1. Initial Build & Prime Hash Cache
        graph = build_graph(self.temp_dir)
        snapshot_mgr = SnapshotManager(snapshot_dir=self.cache_dir)
        snapshot_mgr.save_snapshot(graph, "graph")

        change_detector = ChangeDetector()
        change_detector.get_changed_files(self.temp_dir)

        rel_file1 = "file1.js"
        rel_file2 = "file2.js"


        # Verify initial function nodes
        funcs_file1 = [fn.get("name") if isinstance(fn, dict) else fn for fn in graph["functions"].get(rel_file1, [])]
        funcs_file2 = [fn.get("name") if isinstance(fn, dict) else fn for fn in graph["functions"].get(rel_file2, [])]
        self.assertIn("initialFunc", funcs_file1)
        self.assertIn("untouchedFunc", funcs_file2)

        # 2. Modify file1.js (add a new function)
        with open(file1, "w", encoding="utf-8") as f:
            f.write("function initialFunc() { return 42; }\nfunction newlyAddedFunc(a, b) { return a + b; }\n")

        # 3. Detect changes
        change_detector = ChangeDetector()
        changed_files = change_detector.get_changed_files(self.temp_dir)
        self.assertIn(rel_file1, changed_files)
        self.assertNotIn(rel_file2, changed_files)

        # 4. Invalidate only file1.js
        invalidator = GraphInvalidator()
        invalidator.invalidate_file(graph, rel_file1)

        # Assert file1.js entries are cleared from graph, but file2.js is intact
        self.assertNotIn(rel_file1, graph["functions"])
        self.assertIn(rel_file2, graph["functions"])

        # 5. Rebuild only file1.js
        from language_config import LANG_CONFIG
        from tree_sitter import Parser, Query, QueryCursor
        js_lang = LANG_CONFIG[".js"]["LANGUAGE"]
        parser = Parser(js_lang)
        with open(file1, "r", encoding="utf-8") as f:
            code = f.read()
        tree = parser.parse(bytes(code, "utf-8"))
        query = Query(js_lang, LANG_CONFIG[".js"]["MASTER_QUERY"])
        raw_matches = QueryCursor(query).matches(tree.root_node)
        matches = safe_extract_semantic_matches(raw_matches, rel_file1, tree)


        builder = GraphBuilder()
        builder.graph = graph
        builder.build_file(rel_file1, matches)
        builder.build_argument_parameter_flow()




        # Save snapshot
        snapshot_mgr.save_snapshot(builder.graph, "graph")

        # 6. Verify updated graph state
        updated_funcs_file1 = [fn.get("name") if isinstance(fn, dict) else fn for fn in builder.graph["functions"].get(rel_file1, [])]
        updated_funcs_file2 = [fn.get("name") if isinstance(fn, dict) else fn for fn in builder.graph["functions"].get(rel_file2, [])]

        self.assertIn("initialFunc", updated_funcs_file1)
        self.assertIn("newlyAddedFunc", updated_funcs_file1)
        self.assertIn("untouchedFunc", updated_funcs_file2)


if __name__ == "__main__":
    unittest.main()
