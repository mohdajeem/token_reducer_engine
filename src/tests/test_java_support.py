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

class TestJavaSupport(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_java_parsing_and_call_resolution(self):
        """Test that Java/Spring Boot code is parsed and imports/calls resolve correctly."""
        # 1. Recreate Java package directory structures
        service_dir = os.path.join(self.temp_dir, "src", "main", "java", "com", "example", "service")
        controller_dir = os.path.join(self.temp_dir, "src", "main", "java", "com", "example", "controller")
        os.makedirs(service_dir, exist_ok=True)
        os.makedirs(controller_dir, exist_ok=True)

        service_file = os.path.join(service_dir, "UserService.java")
        controller_file = os.path.join(controller_dir, "UserController.java")

        # 2. Write Java mock source files
        with open(service_file, "w", encoding="utf-8") as f:
            f.write(
                "package com.example.service;\n"
                "public class UserService {\n"
                "  public String fetchUser() {\n"
                "    return \"Ajeem\";\n"
                "  }\n"
                "}\n"
            )

        with open(controller_file, "w", encoding="utf-8") as f:
            f.write(
                "package com.example.controller;\n"
                "import com.example.service.UserService;\n"
                "public class UserController {\n"
                "  private UserService userService = new UserService();\n"
                "  public String getUser() {\n"
                "    return userService.fetchUser();\n"
                "  }\n"
                "}\n"
            )

        # 3. Compile semantic graph
        graph = build_graph(self.temp_dir)

        # 4. Verify function definitions (methods)
        # Note: Paths in graph are relative to temp_dir, and formatted with slashes
        rel_service = "src/main/java/com/example/service/UserService.java"
        rel_controller = "src/main/java/com/example/controller/UserController.java"

        # the class itself is a node too (kind="class"); count the methods
        funcs_service = [f for f in graph.get("functions", {}).get(rel_service, []) if f.get("kind") != "class"]
        self.assertEqual(len(funcs_service), 1)
        self.assertEqual(funcs_service[0].get("name"), "fetchUser")

        funcs_controller = graph.get("functions", {}).get(rel_controller, [])
        # UserController constructor might be implicit or we match getUser
        method_names = [fn.get("name") for fn in funcs_controller]
        self.assertIn("getUser", method_names)

        # 5. Verify call resolution
        # `new X()` is a call record too now (constructor blast radius): look at the method call
        calls = [c for c in graph.get("calls", {}).get(rel_controller, []) if c.get("function") == "fetchUser"]
        self.assertEqual(len(calls), 1)

        call_entry = calls[0]
        self.assertEqual(call_entry.get("object"), "UserService")
        self.assertEqual(call_entry.get("function"), "fetchUser")
        self.assertEqual(call_entry.get("resolved_file"), rel_service)
        self.assertIsNotNone(call_entry.get("resolved_function"))
        self.assertEqual(call_entry["resolved_function"].get("name"), "fetchUser")

if __name__ == "__main__":
    unittest.main()
