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
        # Discovered, not hand-listed. The previous literal held 13 names while tests/
        # contained 35 files; the 22 that were missing had simply been added after someone
        # last edited this list, and nothing pointed that out.
        self.results = {p.name: None for p in sorted(self.test_dir.glob("test_*.py"))}


    
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
            # Through pytest, so pytest-style files actually execute. Run as a plain script,
            # a file whose tests are module-level `def test_x()` functions with no __main__
            # block defines them, exits 0, and is recorded as a pass having asserted nothing.
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), "-q", "-p", "no:warnings"],
                # from src/, because the test modules import the engine by top-level name
                # (`from build_graph import ...`); from tests/ that is a ModuleNotFoundError
                # at collection time, which scores as a failing test rather than a bad command
                cwd=str(self.test_dir.parent),
                capture_output=False,
                timeout=120
            )
            if result.returncode == 5:
                # exit 5 = pytest collected nothing: a script-style test, run it directly
                print(f"[INFO] {test_name}: no pytest tests collected, running as a script")
                result = subprocess.run(
                    [sys.executable, str(test_path)],
                    cwd=str(self.test_dir),
                    capture_output=False,
                    timeout=120
                )
            success = result.returncode == 0
            self.results[test_name] = success
            return success
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] Test exceeded 120 seconds")
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
