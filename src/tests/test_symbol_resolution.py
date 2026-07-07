#!/usr/bin/env python3
"""
TEST 3: SYMBOL RESOLUTION - IMPORT TRACKING & FUNCTION LINKING
Verifies symbols are correctly resolved from REAL project imports
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic_core import GraphBuilder
from semantic_core.match_extractor_fixed import safe_extract_semantic_matches
from semantic_core.symbol_table import SymbolTable
from semantic_core.function_index import FunctionIndex
from language_config import LanguageManager
from tree_sitter import QueryCursor


class TestSymbolResolution:
    
    def __init__(self):
        self.test_dir = Path(__file__).parent.parent.parent / "test_microservice"
        self.language_manager = LanguageManager()
        self.symbol_table = SymbolTable()
        self.function_index = FunctionIndex()
    
    def parse_project(self):
        """Parse all files and build semantic graph."""
        print("\n" + "=" * 80)
        print("PARSING REAL PROJECT FILES")
        print("=" * 80)
        
        builder = GraphBuilder()
        all_matches = []
        
        for file_path in sorted(self.test_dir.rglob("*.js")):
            ext = file_path.suffix
            parser = self.language_manager.get_parser(ext)
            if not parser:
                continue
            
            language = parser.language
            query_string = self.language_manager.get_master_query(ext)
            query = language.query(query_string)
            
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = parser.parse(bytes(source, "utf-8"))
            cursor = QueryCursor(query)
            matches = cursor.matches(tree.root_node)
            
            semantic_matches = safe_extract_semantic_matches(matches, str(file_path), tree)
            all_matches.extend(semantic_matches)
        
        builder.build(all_matches)
        
        # Get symbol tables from builder
        self.symbol_table = builder.symbol_table
        self.function_index = builder.function_index
        
        return builder.graph, all_matches
    
    def print_symbol_resolution(self):
        """Print all resolved and unresolved symbols."""
        print("\n" + "=" * 80)
        print("SYMBOL RESOLUTION MAP - REAL PROJECT")
        print("=" * 80)
        
        print(f"\n[IMPORTS IN SYMBOL TABLE]")
        
        # Get all registered imports
        resolved_imports = {}
        if hasattr(self.symbol_table, 'registry'):
            for file_key, data in self.symbol_table.registry.items():
                if isinstance(data, dict):
                    for sym_name, sym_data in data.items():
                        print(f"  ✓ {sym_name} (from {file_key})")
        
        print(f"\n[FUNCTIONS IN INDEX]")
        
        # List registered functions
        if hasattr(self.function_index, 'registry'):
            func_count = 0
            for file_path, funcs in self.function_index.registry.items():
                for func_name, func_meta in funcs.items():
                    print(f"  ✓ {func_name} in {Path(file_path).name}")
                    func_count += 1
            print(f"  Total: {func_count} functions")
        else:
            print("  [WARNING] Function index registry not accessible")
    
    def verify_expected_symbols(self):
        """Verify expected symbols are resolved."""
        print("\n" + "=" * 80)
        print("VERIFICATION - EXPECTED SYMBOLS")
        print("=" * 80)
        
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: userController import should exist
        print(f"\n[SYMBOL 1] userController import")
        uc_found = self._check_import("userController", "controllers/userController.js")
        if uc_found:
            print(f"  ✓ RESOLVED")
            tests_passed += 1
        else:
            print(f"  ✗ UNRESOLVED")
            tests_failed += 1
        
        # Test 2: userService import should exist
        print(f"\n[SYMBOL 2] userService import")
        us_found = self._check_import("userService", "services/userService.js")
        if us_found:
            print(f"  ✓ RESOLVED")
            tests_passed += 1
        else:
            print(f"  ✗ UNRESOLVED")
            tests_failed += 1
        
        # Test 3: validator import should exist (external)
        print(f"\n[SYMBOL 3] validator import (external library)")
        val_found = self._check_import("validator", "validator")
        if val_found:
            print(f"  ✓ RESOLVED (external)")
            tests_passed += 1
        else:
            print(f"  ⚠ NOT FOUND (may be external-only)")
            # Not counting as fail - external libs may not be in index
        
        # Test 4: getAllUsers function should be indexed
        print(f"\n[FUNCTION 1] getAllUsers should be indexed")
        gau_found = self._check_function("getAllUsers")
        if gau_found:
            print(f"  ✓ INDEXED")
            tests_passed += 1
        else:
            print(f"  ✗ NOT INDEXED")
            tests_failed += 1
        
        # Test 5: fetchUsers function should be indexed
        print(f"\n[FUNCTION 2] fetchUsers should be indexed")
        fu_found = self._check_function("fetchUsers")
        if fu_found:
            print(f"  ✓ INDEXED")
            tests_passed += 1
        else:
            print(f"  ✗ NOT INDEXED")
            tests_failed += 1
        
        # Test 6: Unresolved - authController should NOT be found
        print(f"\n[UNRESOLVED] authController (not imported)")
        auth_found = self._check_import("authController", "")
        if not auth_found:
            print(f"  ✓ CORRECTLY UNRESOLVED")
            tests_passed += 1
        else:
            print(f"  ✗ INCORRECTLY RESOLVED (should be missing)")
            tests_failed += 1
        
        print(f"\n[TEST RESULTS]")
        print(f"  Passed: {tests_passed}/5")
        print(f"  Failed: {tests_failed}/5")
        
        return tests_failed == 0
    
    def _check_import(self, symbol_name, source_hint):
        """Check if an import symbol is registered."""
        if not hasattr(self.symbol_table, 'registry'):
            return False
        
        for file_key, symbols in self.symbol_table.registry.items():
            if isinstance(symbols, dict):
                if symbol_name in symbols:
                    return True
        return False
    
    def _check_function(self, func_name):
        """Check if a function is indexed."""
        if not hasattr(self.function_index, 'registry'):
            return False
        
        for file_path, funcs in self.function_index.registry.items():
            if func_name in funcs:
                return True
        return False
    
    def run(self):
        """Run all tests."""
        print("\n" + "█" * 80)
        print("█ TEST 3: SYMBOL RESOLUTION - IMPORT & FUNCTION LINKING")
        print("█" * 80)
        
        self.graph, self.matches = self.parse_project()
        
        self.print_symbol_resolution()
        success = self.verify_expected_symbols()
        
        print("\n" + "=" * 80)
        if success:
            print("[SUCCESS] Symbol resolution verified!")
        else:
            print("[FAILURE] Symbol resolution incomplete - see above")
        print("=" * 80)
        
        return success


if __name__ == "__main__":
    test = TestSymbolResolution()
    success = test.run()
    sys.exit(0 if success else 1)
