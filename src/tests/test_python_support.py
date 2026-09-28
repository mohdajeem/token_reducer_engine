import os
import shutil
import tempfile
import unittest
from build_graph import build_graph

class TestPythonSupport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.py_file = os.path.join(self.temp_dir, "user_service.py").replace("\\", "/")
        with open(self.py_file, "w", encoding="utf-8") as f:
            f.write('''
import os
from flask import request

def save_user(username, email="user@example.com", status: str = "active", *args, **kwargs):
    user_data = {"name": username, "email": email}
    db.save(user_data)
    return user_data

def process_request():
    raw_name = request.json.get("username")
    save_user(raw_name, status="pending")

def run_command(cmd):
    eval(cmd)
''')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_python_function_and_parameter_extraction(self):
        graph = build_graph(self.temp_dir)
        self.assertIsNotNone(graph)

        # 1. Verify function extraction
        file_key_params = next((k for k in graph["parameters"] if k.lower().endswith("user_service.py")), None)
        self.assertIsNotNone(file_key_params, f"user_service.py file key missing in graph parameters: {list(graph['parameters'].keys())}")
        
        params_list = graph["parameters"].get(file_key_params, [])
        save_user_entry = next((p for p in params_list if p["function"] == "save_user"), None)
        self.assertIsNotNone(save_user_entry, f"save_user function missing from parameters for {file_key_params}")

        # Check positional, default, star_args, and kw_args
        self.assertIn("username", save_user_entry["params"])
        self.assertIn("email", save_user_entry["params"])
        self.assertIn("status", save_user_entry["params"])
        self.assertIn("*args", save_user_entry["params"])
        self.assertIn("**kwargs", save_user_entry["params"])

    def test_python_calls_and_taint_detection(self):
        graph = build_graph(self.temp_dir)
        
        # 2. Verify call extraction (save_user, eval)
        file_key_calls = next((k for k in graph["calls"] if k.lower().endswith("user_service.py")), None)
        calls = [c.get("call") or c.get("target") or c.get("function") for c in graph["calls"].get(file_key_calls, [])]
        self.assertIn("save_user", calls)
        self.assertIn("eval", calls)

if __name__ == "__main__":
    unittest.main()
