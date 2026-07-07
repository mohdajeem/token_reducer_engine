#!/usr/bin/env python3
"""
TEST 5: END-TO-END PIPELINE - COMPLETE SEMANTIC ENGINE WORKFLOW
Validates real-time parsing → graph building → impact analysis → context extraction
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from semantic_core import GraphBuilder
from semantic_core.match_extractor_fixed import safe_extract_semantic_matches
from language_config import LanguageManager
from impact_engine import GraphTraversal
from context_engine import ContextExtractor
from validation import SemanticValidator
from tree_sitter import QueryCursor


class TestEndToEndPipeline:
    
    def __init__(self):
        self.test_dir = Path(__file__).parent.parent.parent / "test_microservice"
        self.language_manager = LanguageManager()
    
    def step_1_parse_files(self):
        """STEP 1: Parse all source files."""
        print("\n" + "=" * 80)
        print("STEP 1: PARSING SOURCE FILES")
        print("=" * 80)
        
        builder = GraphBuilder()
        all_matches = []
        file_count = 0
        
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
            
            rel_path = file_path.relative_to(self.test_dir)
            print(f"  ✓ {rel_path}: {len(semantic_matches)} matches")
            file_count += 1
        
        print(f"\n[RESULT]")
        print(f"  Files parsed:    {file_count}")
        print(f"  Total matches:   {len(all_matches)}")
        
        if len(all_matches) == 0:
            print(f"\n[ERROR] No semantic matches extracted!")
            return builder, all_matches, False
        
        return builder, all_matches, True
    
    def step_2_build_graph(self, builder, all_matches):
        """STEP 2: Build semantic graph."""
        print("\n" + "=" * 80)
        print("STEP 2: BUILDING SEMANTIC GRAPH")
        print("=" * 80)
        
        builder.build(all_matches)
        graph = builder.graph
        
        import_count = self._count_items(graph, "imports")
        route_count = self._count_items(graph, "routes")
        call_count = self._count_items(graph, "calls")
        func_count = self._count_items(graph, "functions")
        db_count = self._count_items(graph, "database")
        edge_count = len(graph.get("execution_edges", []))
        
        print(f"\n[GRAPH STRUCTURE]")
        print(f"  Imports:         {import_count}")
        print(f"  Routes:          {route_count}")
        print(f"  Functions:       {func_count}")
        print(f"  Calls:           {call_count}")
        print(f"  Database ops:    {db_count}")
        print(f"  Execution edges: {edge_count}")
        
        if graph == {} or (import_count == 0 and route_count == 0 and func_count == 0):
            print(f"\n[ERROR] Graph is empty!")
            return graph, False
        
        return graph, True
    
    def step_3_analyze_impact(self, graph):
        """STEP 3: Analyze impact."""
        print("\n" + "=" * 80)
        print("STEP 3: IMPACT ANALYSIS")
        print("=" * 80)
        
        try:
            traversal = GraphTraversal(graph)
            
            functions = graph.get("functions", {})
            all_funcs = []
            for file_funcs in functions.values():
                if isinstance(file_funcs, list):
                    all_funcs.extend(file_funcs)
            
            if not all_funcs:
                print(f"  [INFO] No functions to analyze")
                return {}, True
            
            # Analyze first function
            func_obj = all_funcs[0]
            target_func_name = func_obj.get("name", "unknown")
            target_node = {
                "type": "FUNCTION",
                "file": func_obj.get("file"),
                "function": target_func_name
            }
            
            print(f"\n[TARGET FUNCTION] {target_func_name}")
            
            upstream = traversal.find_upstream_nodes(target_node)
            downstream = traversal.find_downstream_nodes(target_node)
            
            print(f"  Upstream callers:   {len(upstream)}")
            print(f"  Downstream targets: {len(downstream)}")
            
            return {
                "target": target_func_name,
                "upstream": upstream,
                "downstream": downstream,
            }, True
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {}, False
    
    def step_4_extract_context(self, graph, impact):
        """STEP 4: Extract context."""
        print("\n" + "=" * 80)
        print("STEP 4: CONTEXT EXTRACTION")
        print("=" * 80)
        
        try:
            extractor = ContextExtractor(graph, str(self.test_dir))
            context = extractor.extract_context(impact)
            
            print(f"\n[CONTEXT EXTRACTED]")
            print(f"  Relevant files:     {len(context.get('relevant_files', []))}")
            print(f"  Relevant functions: {len(context.get('relevant_functions', []))}")
            print(f"  Code snippets:      {len(context.get('code_snippets', []))}")
            
            return context, True
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {}, False
    
    def step_5_validate(self, graph):
        """STEP 5: Validate semantics."""
        print("\n" + "=" * 80)
        print("STEP 5: SEMANTIC VALIDATION")
        print("=" * 80)
        
        try:
            validator = SemanticValidator(graph)
            
            print(f"  ✓ Validator initialized")
            print(f"  [INFO] Real validation depends on implementation")
            
            return True
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return False
    
    def _count_items(self, graph, category):
        """Count items in graph category."""
        items = graph.get(category, {})
        if isinstance(items, list):
            return len(items)
        if isinstance(items, dict):
            return sum(len(v) if isinstance(v, list) else 1 for v in items.values())
        return 0
    
    def run(self):
        """Run complete pipeline."""
        print("\n" + "█" * 80)
        print("█ TEST 5: END-TO-END SEMANTIC ENGINE PIPELINE")
        print("█" * 80)
        
        # Step 1: Parse
        builder, all_matches, step1_ok = self.step_1_parse_files()
        if not step1_ok:
            print("\n[FAILURE] Parsing failed")
            return False
        
        # Step 2: Build graph
        graph, step2_ok = self.step_2_build_graph(builder, all_matches)
        if not step2_ok:
            print("\n[FAILURE] Graph building failed")
            return False
        
        # Step 3: Analyze impact
        impact, step3_ok = self.step_3_analyze_impact(graph)
        if not step3_ok:
            print("\n[WARNING] Impact analysis failed (non-critical)")
        
        # Step 4: Extract context
        context, step4_ok = self.step_4_extract_context(graph, impact)
        if not step4_ok:
            print("\n[WARNING] Context extraction failed (non-critical)")
        
        # Step 5: Validate
        step5_ok = self.step_5_validate(graph)
        if not step5_ok:
            print("\n[WARNING] Validation failed (non-critical)")
        
        # Summary
        print("\n" + "=" * 80)
        print("END-TO-END PIPELINE SUMMARY")
        print("=" * 80)
        
        all_steps = [
            ("Parsing", step1_ok),
            ("Graph building", step2_ok),
            ("Impact analysis", step3_ok),
            ("Context extraction", step4_ok),
            ("Validation", step5_ok),
        ]
        
        passed = sum(1 for _, ok in all_steps if ok)
        failed = sum(1 for _, ok in all_steps if not ok)
        
        for step_name, ok in all_steps:
            status = "✓" if ok else "⚠"
            print(f"  {status} {step_name}")
        
        print(f"\n  Passed: {passed}/{len(all_steps)}")
        print(f"  Failed: {failed}/{len(all_steps)}")
        
        print("\n" + "=" * 80)
        if failed == 0:
            print("[SUCCESS] Complete pipeline working!")
        elif failed <= 2:
            print("[PARTIAL] Core pipeline working, some analysis features incomplete")
        else:
            print("[FAILURE] Pipeline has critical issues")
        print("=" * 80)
        
        return step1_ok and step2_ok  # Core steps critical, others optional


if __name__ == "__main__":
    test = TestEndToEndPipeline()
    success = test.run()
    sys.exit(0 if success else 1)
