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
from semantic_core.symbol_resolver import SymbolResolver

class TestTypeResolution(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_instantiation_extraction(self):
        """Test parsing of constructor values to extract class name."""
        self.assertEqual(SymbolResolver.extract_instantiated_class("new User()"), "User")
        self.assertEqual(SymbolResolver.extract_instantiated_class("  new Product(1, 2)  "), "Product")
        self.assertEqual(SymbolResolver.extract_instantiated_class("User()"), "User")
        self.assertEqual(SymbolResolver.extract_instantiated_class("Product('arg')"), "Product")
        self.assertIsNone(SymbolResolver.extract_instantiated_class("someFunction()"))
        self.assertIsNone(SymbolResolver.extract_instantiated_class("42"))

    def test_end_to_end_class_method_resolution(self):
        """Test that instantiations dynamically map method calls to the target class definitions."""
        model_file = os.path.join(self.temp_dir, "user.js")
        controller_file = os.path.join(self.temp_dir, "controller.js")

        # 1. Write mock files
        with open(model_file, "w", encoding="utf-8") as f:
            f.write("export class User {\n  find() { return []; }\n}\n")

        with open(controller_file, "w", encoding="utf-8") as f:
            f.write("import { User } from './user';\nfunction get() {\n  const u = new User();\n  return u.find();\n}\n")

        # 2. Build graph
        graph = build_graph(self.temp_dir)

        # 3. Verify call resolution
        # `new X()` is a call record too now (constructor blast radius): look at the method call
        calls = [c for c in graph.get("calls", {}).get("controller.js", []) if c.get("function") == "find"]
        self.assertEqual(len(calls), 1)
        
        call_entry = calls[0]
        self.assertEqual(call_entry.get("object"), "User")
        self.assertEqual(call_entry.get("function"), "find")
        self.assertEqual(call_entry.get("resolved_file"), "user.js")
        self.assertIsNotNone(call_entry.get("resolved_function"))
        self.assertEqual(call_entry["resolved_function"].get("name"), "find")

if __name__ == "__main__":
    unittest.main()
