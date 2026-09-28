#!/usr/bin/env python3
"""
Unit tests for Object Destructuring, Rest Parameters, and Keyword Object Data Flow Mapping.
"""

import unittest
import tempfile
import os
from pathlib import Path
import shutil

from semantic_core.graph_builder import GraphBuilder
from build_graph import build_graph

class TestParameterFlow(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_destructured_and_rest_parameters(self):
        """Test parameter extraction for destructured object params and rest params."""
        code = """
        function saveUser({ name, email }, status) {
            return db.save({ name, email });
        }

        function logActivity(level, ...messages) {
            console.log(level, messages);
        }

        const run = async () => {
            saveUser({ name: req.body.name, email: req.body.email }, 200);
            logActivity('info', 'user logged in', 'session created');
        };
        """
        file_path = os.path.join(self.temp_dir, "test.js")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

        graph = build_graph(self.temp_dir)
        
        # Verify parameters extracted
        func_params = {}
        for file_key, params_list in graph["parameters"].items():
            for p in params_list:
                func_params[p["function"]] = p["params"]


        self.assertIn("saveUser", func_params)
        self.assertIn("name", func_params["saveUser"])
        self.assertIn("email", func_params["saveUser"])
        self.assertIn("status", func_params["saveUser"])

        self.assertIn("logActivity", func_params)
        self.assertIn("level", func_params["logActivity"])
        self.assertIn("...messages", func_params["logActivity"])

        # Verify data flow mappings
        data_flows = graph.get("data_flow", [])
        
        # Check destructuring mapping from object argument { name: req.body.name, email: req.body.email }
        destructured_flows = [df for df in data_flows if df["target_function"] == "saveUser"]
        sources = {df["target_param"]: df["source"] for df in destructured_flows}
        
        self.assertIn("name", sources)
        self.assertEqual(sources["name"], "req.body.name")
        self.assertIn("email", sources)
        self.assertEqual(sources["email"], "req.body.email")

        # Check rest parameter flow mapping
        rest_flows = [df for df in data_flows if df["target_function"] == "logActivity"]
        mapped_to_rest = [df["source"] for df in rest_flows if df["target_param"] == "messages"]
        
        self.assertIn("'user logged in'", mapped_to_rest)
        self.assertIn("'session created'", mapped_to_rest)

if __name__ == "__main__":
    unittest.main()
