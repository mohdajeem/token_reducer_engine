import os
import sys
import unittest
from pathlib import Path

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from benchmark.sandbox_manager import SandboxManager
from benchmark.model_client import MockModelClient
from benchmark.patch_applier import PatchApplier
from benchmark.safety_checker import SafetyChecker
from benchmark.scoring_engine import ScoringEngine
from benchmark.task_runner import BenchmarkRunner

class TestBenchmarkHarness(unittest.TestCase):
    
    def setUp(self):
        self.project_root = current_file.parent.parent.parent
        self.test_microservice = os.path.abspath(os.path.join(self.project_root, "test_microservice"))
        self.testing1 = os.path.abspath(r"C:\Users\ajeem\Downloads\downloads\testing\testing1")
        
    def test_sandbox_manager(self):
        print("Testing SandboxManager...")
        sandbox = SandboxManager(self.test_microservice)
        sandbox_path = sandbox.setup_sandbox()
        self.assertTrue(os.path.exists(sandbox_path))
        self.assertTrue(os.path.exists(os.path.join(sandbox_path, "api.js")))
        
        # Test command runner
        res = sandbox.run_command("node -v")
        self.assertTrue(res["passed"] or res["exit_code"] != 0) # node might not be present or exits with code
        
        sandbox.cleanup_sandbox()
        self.assertFalse(os.path.exists(sandbox_path))
        
    def test_mock_model_client(self):
        print("Testing MockModelClient...")
        client = MockModelClient()
        patch1 = client.generate_patch("", "task_modify_get_user")
        self.assertIn("Ajeem Modified", patch1)
        
        patch2 = client.generate_patch("", "task_lockout_policy")
        self.assertIn("failedAttempts >= 5", patch2)
        
    def test_patch_applier(self):
        print("Testing PatchApplier...")
        sandbox = SandboxManager(self.test_microservice)
        sandbox_path = sandbox.setup_sandbox()
        
        patch_text = """```diff
--- api.js
+++ api.js
@@ -8,3 +8,3 @@
 const getUserById = () => {
-    return { "user": "Ajeem" };
+    return { "user": "Ajeem Modified" };
 }
```"""
        res = PatchApplier.apply_patch(sandbox_path, patch_text)
        self.assertTrue(res["success"], f"Error: {res['error']}")
        self.assertIn("api.js", res["applied_files"])
        
        # Read file and verify modification
        with open(os.path.join(sandbox_path, "api.js"), "r", encoding="utf-8") as f:
            code = f.read()
            self.assertIn("Ajeem Modified", code)
            self.assertNotIn("return { \"user\": \"Ajeem\" };", code)
            
        sandbox.cleanup_sandbox()
        
    def test_scoring_engine(self):
        print("Testing ScoringEngine...")
        metrics = ScoringEngine.compute_metrics(
            selected_files=["src/routes/auth.routes.js", "src/controllers/auth.controller.js"],
            ground_truth_files=["src/routes/auth.routes.js", "src/controllers/auth.controller.js", "src/services/auth.service.js"],
            context_char_size=2000,
            total_repo_chars=10000,
            safety_results={"findings": []},
            test_passed=True,
            input_tokens=500,
            output_tokens=200,
            model_provider="claude",
            latency=2.5
        )
        
        # Ground truth has 3 files, selected has 2. Recall should be 2/3 = 0.6667
        # Precision should be 2/2 = 1.0
        # Context efficiency: 1 - 2000/10000 = 80.0%
        # Cost: 500 * 3/1e6 + 200 * 15/1e6 = 0.0015 + 0.0030 = 0.0045 USD
        self.assertEqual(metrics["edit_recall"], 0.6667)
        self.assertEqual(metrics["edit_precision"], 1.0)
        self.assertEqual(metrics["context_efficiency"], 80.0)
        self.assertEqual(metrics["cost_usd"], 0.0045)
        self.assertEqual(metrics["test_pass_rate"], 1.0)
        
    def test_end_to_end_runner(self):
        print("Testing End-To-End BenchmarkRunner with MockModelClient...")
        client = MockModelClient()
        
        # Define tasks (scope to test_microservice only to run fully offline and fast)
        tasks = [
            {
                "task_id": "task_modify_get_user",
                "name": "Modify getUserById in microservice",
                "repository_path": self.test_microservice,
                "query_target": "FUNCTION:api.js:getUserById",
                "traversal_policy": "DEFAULT",
                "engineering_prompt": "Modify the getUserById function in api.js to return the username 'Ajeem Modified' instead of 'Ajeem'.",
                "ground_truth_files": ["api.js"],
                "test_command": "node -e \"const fs = require('fs'); const code = fs.readFileSync('api.js', 'utf8'); if (!code.includes('Ajeem Modified')) { console.error('FAILED - getUserById not modified'); process.exit(1); } console.log('PASSED - getUserById return value updated successfully');\""
            }
        ]
        
        runner = BenchmarkRunner(model_client=client, tasks=tasks)
        res = runner.run_benchmarks()
        
        self.assertIn("summary", res)
        self.assertIn("results", res)
        self.assertEqual(len(res["results"]), 1)
        self.assertTrue(res["results"][0]["stages"]["test_execution"]["passed"])
        self.assertEqual(res["summary"]["test_pass_rate"], 1.0)
        
        # Check that output files are generated
        self.assertTrue(os.path.exists(os.path.join(self.project_root, "snapshots", "benchmark_results.json")))
        self.assertTrue(os.path.exists(os.path.join(self.project_root, "BENCHMARK_REPORT.md")))

if __name__ == "__main__":
    unittest.main()
