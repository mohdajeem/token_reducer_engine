import os
import unittest
import tempfile
import shutil
import sys
from pathlib import Path

# Add project root and src directories to Python Path
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_path))
sys.path.insert(0, str(root_path / "src"))

from build_graph import build_graph

class TestTypeScriptSupport(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_typescript_parsing_and_resolution(self):
        """Test that TypeScript files are parsed and member calls resolve correctly."""
        service_file = os.path.join(self.temp_dir, "service.ts")
        controller_file = os.path.join(self.temp_dir, "controller.ts")

        # 1. Write mock TypeScript files
        with open(service_file, "w", encoding="utf-8") as f:
            f.write("export class UserService {\n  public getUsers(limit: number): string[] {\n    return ['Ajeem'];\n  }\n}\n")

        with open(controller_file, "w", encoding="utf-8") as f:
            f.write("import { UserService } from './service';\nfunction get() {\n  const service = new UserService();\n  return service.getUsers(10);\n}\n")

        # 2. Build graph
        graph = build_graph(self.temp_dir)

        # 3. Verify function definitions
        # the class itself is a node too (kind="class"); count the methods
        funcs = [f for f in graph.get("functions", {}).get("service.ts", []) if f.get("kind") != "class"]
        self.assertEqual(len(funcs), 1)
        self.assertEqual(funcs[0].get("name"), "getUsers")

        # 4. Verify call resolution
        # `new X()` is a call record too now (constructor blast radius): look at the method call
        calls = [c for c in graph.get("calls", {}).get("controller.ts", []) if c.get("function") == "getUsers"]
        self.assertEqual(len(calls), 1)
        
        call_entry = calls[0]
        self.assertEqual(call_entry.get("object"), "UserService")
        self.assertEqual(call_entry.get("function"), "getUsers")
        self.assertEqual(call_entry.get("resolved_file"), "service.ts")
        self.assertIsNotNone(call_entry.get("resolved_function"))
        self.assertEqual(call_entry["resolved_function"].get("name"), "getUsers")

if __name__ == "__main__":
    unittest.main()
