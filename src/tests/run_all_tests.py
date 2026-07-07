#!/usr/bin/env python3
"""
MASTER TEST SUITE
Complete semantic engine verification on REAL test_microservice project
"""

import os
import sys
import subprocess
from pathlib import Path


class MasterTestRunner:
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = {
            "test_graph_correctness.py": None,
            "test_execution_edges.py": None,
            "test_symbol_resolution.py": None,
            "test_security_analysis.py": None,
            "test_end_to_end_pipeline.py": None,
            "test_traversal_policy.py": None,
            "test_mcp_server.py": None,
            "test_benchmark_harness.py": None,
        }
    
    def run_test(self, test_name):
        """Run a single test file."""
        test_path = self.test_dir / test_name
        
        if not test_path.exists():
            print(f"[ERROR] Test not found: {test_name}")
            return False
        
        print(f"\n{'=' * 80}")
        print(f"RUNNING: {test_name}")
        print(f"{'=' * 80}\n")
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_path)],
                cwd=str(self.test_dir),
                capture_output=False,
                timeout=60
            )
            success = result.returncode == 0
            self.results[test_name] = success
            return success
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] Test exceeded 60 seconds")
            self.results[test_name] = False
            return False
        except Exception as e:
            print(f"[ERROR] {e}")
            self.results[test_name] = False
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "█" * 80)
        print("█ MASTER TEST SUITE - SUMMARY")
        print("█" * 80)
        
        passed = sum(1 for v in self.results.values() if v)
        failed = sum(1 for v in self.results.values() if v is False)
        
        print(f"\n[RESULTS]")
        for test_name, result in self.results.items():
            status = "✓ PASS" if result else ("✗ FAIL" if result is False else "⚠ SKIP")
            print(f"  {status:8} {test_name}")
        
        print(f"\n[SUMMARY]")
        print(f"  Passed: {passed}/{len(self.results)}")
        print(f"  Failed: {failed}/{len(self.results)}")
        
        print(f"\n[VERDICT]")
        if failed == 0:
            print(f"  ✓ ALL TESTS PASSED - Engine is working correctly!")
        elif passed > failed:
            print(f"  ⚠ PARTIAL SUCCESS - Some features need fixing")
        else:
            print(f"  ✗ CRITICAL FAILURES - Engine needs major fixes")
        
        print("\n" + "█" * 80)
        
        return failed == 0
    
    def run(self):
        """Run all tests."""
        print("\n" + "█" * 80)
        print("█ SEMANTIC ENGINE - REAL PROJECT TEST SUITE")
        print("█ Project: test_microservice/")
        print("█ Mode: REAL EXECUTION (NOT mocked)")
        print("█" * 80)
        
        # Run all tests
        for test_name in self.results.keys():
            self.run_test(test_name)
        
        # Print summary
        all_passed = self.print_summary()
        
        return all_passed


if __name__ == "__main__":
    runner = MasterTestRunner()
    success = runner.run()
    sys.exit(0 if success else 1)
