import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from api.mcp_server import mcp_build_graph, mcp_query_context, SERVER_STATE
from benchmark.sandbox_manager import SandboxManager
from benchmark.model_client import ModelClient, MockModelClient
from benchmark.patch_applier import PatchApplier
from benchmark.safety_checker import SafetyChecker
from benchmark.scoring_engine import ScoringEngine

class BenchmarkRunner:
    """
    Orchestrates the AI Benchmark Harness V1 execution pipeline.
    Loads tasks, fetches MCP context, requests patches from AI clients,
    evaluates semantic safety, runs sandboxed test suites, and generates reports.
    """
    def __init__(self, model_client: ModelClient, tasks: List[Dict[str, Any]] = None):
        self.model_client = model_client
        self.tasks = tasks or self._get_default_tasks()
        
    def _get_default_tasks(self) -> List[Dict[str, Any]]:
        project_root = current_file.parent.parent.parent
        test_microservice = os.path.abspath(os.path.join(project_root, "test_microservice"))
        testing1 = os.path.abspath(r"C:\Users\ajeem\Downloads\downloads\testing\testing1")
        
        return [
            {
                "task_id": "task_modify_get_user",
                "name": "Modify getUserById in microservice",
                "repository_path": test_microservice,
                "query_target": "FUNCTION:api.js:getUserById",
                "traversal_policy": "DEFAULT",
                "engineering_prompt": "Modify the getUserById function in api.js to return the username 'Ajeem Modified' instead of 'Ajeem'.",
                "ground_truth_files": ["api.js"],
                "test_command": "node -e \"const fs = require('fs'); const code = fs.readFileSync('api.js', 'utf8'); if (!code.includes('Ajeem Modified')) { console.error('FAILED - getUserById not modified'); process.exit(1); } console.log('PASSED - getUserById return value updated successfully');\""
            },
            {
                "task_id": "task_lockout_policy",
                "name": "Implement lockout policy on auth service",
                "repository_path": testing1,
                "query_target": "ROUTE:post:/login:src/routes/auth.routes.js",
                "traversal_policy": "NEW_FEATURE",
                "engineering_prompt": "Implement a lockout policy in src/services/auth.service.js: if user.failedAttempts >= 5, throw a forbidden CustomError that says 'Account is locked due to multiple failed login attempts'.",
                "ground_truth_files": ["src/services/auth.service.js"],
                "test_command": "node test-flow.js"
            }
        ]
        
    def _calculate_repo_size(self, repo_path: str) -> int:
        total_chars = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "dist", "build", ".venv", "venv", ".sandbox")]
            for file in files:
                if file.endswith((".js", ".ts", ".py")):
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            total_chars += len(f.read())
                    except:
                        pass
        return total_chars
        
    def run_benchmarks(self) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("🚀 RUNNING AI BENCHMARK HARNESS V1")
        print("="*80)
        
        results = []
        
        for task in self.tasks:
            task_id = task["task_id"]
            name = task["name"]
            repo_path = task["repository_path"]
            query_target = task["query_target"]
            policy = task["traversal_policy"]
            prompt = task["engineering_prompt"]
            ground_truth = task["ground_truth_files"]
            test_cmd = task["test_command"]
            
            if not os.path.exists(repo_path):
                print(f"⚠️ Repository for task '{name}' not found at {repo_path}. Skipping.")
                continue
                
            print(f"\nTask: {name} (ID: {task_id})")
            print(f"  Target: {query_target} | Policy: {policy}")
            
            # 1. Initialize Sandbox
            sandbox = SandboxManager(repo_path)
            sandbox_path = sandbox.setup_sandbox()
            
            # 2. Build Graph & Query Context via MCP Server
            print("  Querying semantic context from MCP Server...")
            mcp_build_graph(sandbox_path, force_rebuild=False)
            context = mcp_query_context(query_target, policy)
            
            # Prepare context metrics
            selected_files = context.get("relevant_files", [])
            snippets_payload = json.dumps(context.get("code_snippets", []))
            context_chars = len(snippets_payload)
            repo_chars = self._calculate_repo_size(sandbox_path)
            
            # 3. Assemble Prompts and generate patch
            system_prompt = (
                "You are an AI programming assistant. You must output code patches to resolve requests.\n"
                "You MUST respond ONLY with valid code modifications enclosed in a markdown code fence.\n"
                "You can use Unified Git Diff format or SEARCH/REPLACE block notation.\n"
                "Do not include explanations or conversational text outside code blocks."
            )
            user_prompt = (
                f"Task ID: {task_id}\n"
                f"Engineering request: {prompt}\n\n"
                f"MCP Context Payload:\n{snippets_payload}"
            )
            
            # Estimate tokens
            input_tokens = len(system_prompt + user_prompt) // 4
            
            print(f"  Requesting patch from model ({self.model_client.model_name})...")
            start_time = time.time()
            raw_response = self.model_client.generate_patch(system_prompt, user_prompt)
            latency = time.time() - start_time
            
            output_tokens = len(raw_response) // 4
            
            # 4. Syntactic and Semantic Safety Checks
            print("  Running AST and semantic safety verification...")
            safety = SafetyChecker.run_checks(
                sandbox_path=sandbox_path,
                graph=SERVER_STATE["graph"],
                file_path=ground_truth[0] if ground_truth else "",
                function_name=query_target.split(":")[-1] if "FUNCTION:" in query_target else "",
                patch_content=raw_response
            )
            
            # 5. Apply Patch
            print("  Applying generated patch to sandboxed workspace...")
            patch_success = False
            patch_error = None
            if safety["syntax_valid"]:
                patch_res = PatchApplier.apply_patch(sandbox_path, raw_response)
                patch_success = patch_res["success"]
                patch_error = patch_res["error"]
                if patch_error:
                    print(f"  ❌ Patch Applier failed: {patch_error}")
            else:
                patch_error = f"AST syntax validation failed: {safety['syntax_reason']}"
                print(f"  ❌ Patch validation failed: {patch_error}")
                
            # 6. Execute Unit/Integration Tests
            test_passed = False
            test_log = ""
            if patch_success:
                print(f"  Executing test command: {test_cmd}...")
                test_res = sandbox.run_command(test_cmd, timeout=30)
                
                # Check for "FAILED" or "❌" inside stdout for test-flow.js fallback
                stdout_log = test_res.get("stdout", "")
                stderr_log = test_res.get("stderr", "")
                test_log = f"STDOUT:\n{stdout_log}\n\nSTDERR:\n{stderr_log}"
                
                if test_res.get("passed", False):
                    # Guard for test-flow.js printing FAILED without throwing exit code
                    if "FAILED" in stdout_log or "❌" in stdout_log:
                        test_passed = False
                    else:
                        test_passed = True
                else:
                    test_passed = False
            else:
                test_log = f"Patch application failed. Skipping tests. Details: {patch_error}"
                
            print(f"  Verdict: Test Suite {'🟢 PASSED' if test_passed else '🔴 FAILED'}")
            
            # 7. Compute Scores
            metrics = ScoringEngine.compute_metrics(
                selected_files=selected_files,
                ground_truth_files=ground_truth,
                context_char_size=context_chars,
                total_repo_chars=repo_chars,
                safety_results=safety,
                test_passed=test_passed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_provider=self.model_client.model_name,
                latency=latency
            )
            
            # 8. Record Results
            results.append({
                "task_id": task_id,
                "name": name,
                "stages": {
                    "context_extraction": {
                        "characters": context_chars,
                        "estimated_tokens": context_chars // 4,
                        "reduction_percentage": round(metrics["context_efficiency"], 2)
                    },
                    "patch_validation": {
                        "syntax_valid": safety["syntax_valid"],
                        "safe_to_apply": safety["safe_to_apply"],
                        "trust_score": metrics["hallucination_rate"], # Use metric rate mapping
                        "findings": safety["findings"]
                    },
                    "test_execution": {
                        "passed": test_passed,
                        "exit_code": 0 if test_passed else 1,
                        "output_log": test_log
                    }
                },
                "metrics": metrics
            })
            
            # Cleanup sandbox
            sandbox.cleanup_sandbox()
            
        # 9. Compute global summary
        summary = self._compute_summary(results)
        
        # Save snapshot
        self._save_results(results, summary)
        
        return {"summary": summary, "results": results}
        
    def _compute_summary(self, results: list) -> dict:
        if not results:
            return {}
        count = len(results)
        avg_recall = sum(r["metrics"]["edit_recall"] for r in results) / count
        avg_precision = sum(r["metrics"]["edit_precision"] for r in results) / count
        avg_efficiency = sum(r["metrics"]["context_efficiency"] for r in results) / count
        avg_hallucination = sum(r["metrics"]["hallucination_rate"] for r in results) / count
        pass_rate = sum(r["metrics"]["test_pass_rate"] for r in results) / count
        total_cost = sum(r["metrics"]["cost_usd"] for r in results)
        avg_latency = sum(r["metrics"]["latency_seconds"] for r in results) / count
        
        return {
            "avg_recall": round(avg_recall, 4),
            "avg_precision": round(avg_precision, 4),
            "avg_context_efficiency": round(avg_efficiency, 2),
            "avg_hallucination_rate": round(avg_hallucination, 2),
            "test_pass_rate": round(pass_rate, 4),
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_seconds": round(avg_latency, 2)
        }
        
    def _save_results(self, results: list, summary: dict):
        project_root = current_file.parent.parent.parent
        snapshots_dir = os.path.join(project_root, "snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)
        
        # Save JSON snapshot
        with open(os.path.join(snapshots_dir, "benchmark_results.json"), "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "results": results}, f, indent=2)
            
        # Save Markdown Report
        markdown = self._generate_markdown_report(results, summary)
        with open(os.path.join(project_root, "BENCHMARK_REPORT.md"), "w", encoding="utf-8") as f:
            f.write(markdown)
            
    def _generate_markdown_report(self, results: list, summary: dict) -> str:
        lines = [
            "# AI Benchmark Harness V1: Evaluation Report",
            f"\nGenerated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Evaluated Model: `{self.model_client.model_name}`\n",
            "## 📊 Global Dashboard",
            "\n| Metric | Average Score | Description |",
            "| :--- | :---: | :--- |",
            f"| **Test Pass Rate (Accuracy)** | **{summary['test_pass_rate']:.1%}** | Percentage of tasks that successfully pass all unit tests. |",
            f"| **Edit Recall** | **{summary['avg_recall']:.1%}** | Percentage of ground-truth files successfully context-extracted. |",
            f"| **Edit Precision** | **{summary['avg_precision']:.1%}** | Tightness of context selection. |",
            f"| **Context Efficiency** | **{summary['avg_context_efficiency']:.1f}%** | Percentage of codebase tokens pruned. |",
            f"| **Hallucination Rate** | **{summary['avg_hallucination_rate']:.1f}%** | Ratio of unresolved symbol references introduced by patch. |",
            f"| **Total API Cost** | **${summary['total_cost_usd']:.6f}** | Total token billing based on pricing model. |",
            f"| **Average Latency** | **{summary['avg_latency_seconds']:.2f}s** | Average model inference wait time. |",
            "\n---",
            "## 📋 Task Evaluation Summary",
            "\n| Task Name | Policy | Recall | Precision | Safety Score | Test Passed | Latency |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
        ]
        
        for r in results:
            passed_symbol = "🟢 PASS" if r["stages"]["test_execution"]["passed"] else "🔴 FAIL"
            lines.append(
                f"| {r['name']} | `{r['metrics']['context_efficiency']:.1f}%` | "
                f"{r['metrics']['edit_recall']:.0%} | {r['metrics']['edit_precision']:.0%} | "
                f"{r['stages']['patch_validation']['trust_score']:.1f}% | {passed_symbol} | {r['metrics']['latency_seconds']:.2f}s |"
            )
            
        lines.append("\n---\n## 🔍 Detailed Task Logs")
        for r in results:
            lines.append(f"\n### {r['name']}")
            lines.append(f"- **Task ID**: `{r['task_id']}`")
            lines.append(f"- **Context Characters**: `{r['stages']['context_extraction']['characters']}` (~{r['stages']['context_extraction']['estimated_tokens']} tokens)")
            lines.append(f"- **AST Validation Status**: `{'Valid' if r['stages']['patch_validation']['syntax_valid'] else 'Syntax Error'}`")
            
            findings = r["stages"]["patch_validation"]["findings"]
            if findings:
                lines.append("- **Findings/Violations Detected**:")
                for f in findings:
                    lines.append(f"  - `[{f.get('type')}]` ({f.get('severity')}): {f.get('message')}")
            else:
                lines.append("- **Findings/Violations Detected**: None")
                
            lines.append(f"\n**Test Log Snippet**:\n```text\n{r['stages']['test_execution']['output_log'][:1000]}\n```\n")
            
        return "\n".join(lines)
