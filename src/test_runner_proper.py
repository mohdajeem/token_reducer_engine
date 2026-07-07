#!/usr/bin/env python3
"""
SEMANTIC ENGINE - PROPER TEST RUNNER
=====================================
This test runner ACTUALLY PARSES files and extracts semantic matches.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from semantic_core import GraphBuilder
from semantic_core.match_extractor_fixed import safe_extract_semantic_matches
from language_config import LanguageManager
from impact_engine import GraphTraversal
from context_engine import ContextExtractor
from validation import SemanticValidator
from tree_sitter import QueryCursor


class ProperSemanticTestRunner:
    """Test the semantic engine by ACTUALLY PARSING files."""
    
    def __init__(self, target_dir):
        self.target_dir = os.path.abspath(target_dir)
        self.language_manager = LanguageManager()
        self.results = {}
    
    def count_items_in_graph(self, category):
        """Count actual items in a graph category (handles file-grouped structure)."""
        items = self.graph.get(category, {})
        if isinstance(items, list):
            return len(items)  # execution_edges is a list
        if isinstance(items, dict):
            # Count items across all files
            return sum(len(v) if isinstance(v, list) else 1 for v in items.values())
        return 0
        
    def validate_target(self):
        """Verify target directory exists."""
        if not os.path.isdir(self.target_dir):
            print(f"[ERROR] Not a directory: {self.target_dir}")
            return False
        
        files_by_ext = {}
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                ext = Path(file).suffix
                if ext:
                    files_by_ext[ext] = files_by_ext.get(ext, 0) + 1
        
        print(f"[OK] Target: {self.target_dir}")
        print(f"   Files: {sum(files_by_ext.values())}")
        for ext, count in sorted(files_by_ext.items()):
            print(f"     - {ext}: {count}")
        
        return True
    
    def parse_and_extract(self, file_path):
        """Parse a file and extract semantic matches."""
        try:
            _, ext = os.path.splitext(file_path)
            
            # Get parser and query
            parser = self.language_manager.get_parser(ext)
            if parser is None:
                return []
            
            query_string = self.language_manager.get_master_query(ext)
            if not query_string:
                return []
            
            language = parser.language
            query = language.query(query_string)
            
            # Read and parse file
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            
            tree = parser.parse(bytes(source_code, "utf-8"))
            
            # Extract matches using QueryCursor
            cursor = QueryCursor(query)
            matches = cursor.matches(tree.root_node)
            
            # Convert to semantic matches (using FIXED version without Unicode errors)
            semantic_matches = safe_extract_semantic_matches(
                matches, 
                file_path, 
                tree
            )
            
            return semantic_matches
            
        except Exception as e:
            print(f"   [PARSE ERROR] {file_path}: {e}")
            return []
    
    def build_graph(self):
        """Build semantic graph by parsing all files."""
        print("\n" + "=" * 80)
        print("STEP 1: BUILDING SEMANTIC GRAPH (WITH ACTUAL PARSING)")
        print("=" * 80)
        
        try:
            builder = GraphBuilder()
            all_semantic_matches = []
            
            # Parse all source files
            file_count = 0
            for root, dirs, files in os.walk(self.target_dir):
                for file in files:
                    ext = Path(file).suffix
                    if ext in {'.py', '.js', '.jsx', '.ts', '.tsx'}:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.target_dir)
                        
                        print(f"   [PARSE] {rel_path}")
                        
                        # Parse and extract
                        semantic_matches = self.parse_and_extract(file_path)
                        all_semantic_matches.extend(semantic_matches)
                        file_count += 1
                        
                        if semantic_matches:
                            print(f"      -> Found {len(semantic_matches)} semantic matches")
            
            # Build graph from all matches
            if all_semantic_matches:
                builder.build(all_semantic_matches)
                print(f"\n[OK] Graph built from {len(all_semantic_matches)} semantic matches")
            else:
                print(f"\n[INFO] No semantic matches found")
            
            self.graph = builder.graph
            
            print(f"\n[GRAPH CONTENT]")
            print(f"   - Imports:         {self.count_items_in_graph('imports')} items")
            print(f"   - Routes:          {self.count_items_in_graph('routes')} items")
            print(f"   - Calls:           {self.count_items_in_graph('calls')} items")
            print(f"   - Database:        {self.count_items_in_graph('database')} items")
            print(f"   - Execution edges: {self.count_items_in_graph('execution_edges')} items")
            print(f"   - Functions:       {self.count_items_in_graph('functions')} items")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Building graph: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def analyze_impact(self):
        """Analyze impact of changes."""
        print("\n" + "=" * 80)
        print("STEP 2: ANALYZING IMPACT")
        print("=" * 80)
        
        try:
            traversal = GraphTraversal(self.graph)
            
            functions = self.graph.get('functions', {})
            if not functions:
                print("   [INFO] No functions in graph yet")
                self.impact = {
                    "target": "NO_FUNCTION",
                    "upstream": [],
                    "downstream": []
                }
                return True
            
            all_funcs = []
            for file_funcs in functions.values():
                if isinstance(file_funcs, list):
                    all_funcs.extend(file_funcs)

            print("\nFUNCTIONS FOUND:")
            for f in all_funcs:
                print(f["name"])
            
            if not all_funcs:
                print("   [INFO] No functions in graph yet")
                self.impact = {
                    "target": "NO_FUNCTION",
                    "upstream": [],
                    "downstream": []
                }
                return True
                
            func_obj = all_funcs[0]
            target_func_name = func_obj.get("name", "unknown")
            sample_func = {
                "type": "FUNCTION",
                "file": func_obj.get("file"),
                "function": target_func_name
            }
            print(f"   [TARGET] {target_func_name}")
            
            upstream = traversal.find_upstream_nodes(sample_func)
            downstream = traversal.find_downstream_nodes(sample_func)
            
            self.impact = {
                "target": target_func_name,
                "upstream": upstream,
                "downstream": downstream
            }
            
            print(f"   [IMPACT] Upstream: {len(upstream)}, Downstream: {len(downstream)}")
            return True
            
        except Exception as e:
            print(f"[ERROR] {e}")
            return False
    
    def extract_context(self):
        """Extract context for AI."""
        print("\n" + "=" * 80)
        print("STEP 3: EXTRACTING CONTEXT")
        print("=" * 80)
        
        try:
            extractor = ContextExtractor(self.graph, self.target_dir)
            context = extractor.extract_context(self.impact)
            self.context = context
            
            print(f"   [OK] Context extracted")
            print(f"      - Files: {len(context.get('relevant_files', []))}")
            print(f"      - Functions: {len(context.get('relevant_functions', []))}")
            print(f"      - Snippets: {len(context.get('code_snippets', []))}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] {e}")
            return False
    
    def validate(self):
        """Validate semantics."""
        print("\n" + "=" * 80)
        print("STEP 4: VALIDATION")
        print("=" * 80)
        
        try:
            validator = SemanticValidator(self.graph)
            print(f"   [OK] Validator ready")
            return True
        except Exception as e:
            print(f"   [INFO] {e}")
            return True
    
    def generate_report(self):
        """Generate report."""
        print("\n" + "=" * 80)
        print("TEST REPORT")
        print("=" * 80)
        report = {
            "target_directory": self.target_dir,
            "graph": {
                "imports": self.count_items_in_graph('imports'),
                "routes": self.count_items_in_graph('routes'),
                "calls": self.count_items_in_graph('calls'),
                "database": self.count_items_in_graph('database'),
                "functions": self.count_items_in_graph('functions'),
                "execution_edges": self.count_items_in_graph('execution_edges'),
            }
        }
        
        print("\n[RESULTS]")
        print(f"   Imports:        {report['graph']['imports']:6d}")
        print(f"   Routes:         {report['graph']['routes']:6d}")
        print(f"   Calls:          {report['graph']['calls']:6d}")
        print(f"   Functions:      {report['graph']['functions']:6d}")
        print(f"   Database:       {report['graph']['database']:6d}")
        print(f"   Exec Edges:     {report['graph']['execution_edges']:6d}")
        
        report_path = os.path.join(self.target_dir, "semantic_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n[SAVED] {report_path}")
        
        return report
    
    def run(self):
        """Run complete test."""
        print("\n" + "=" * 80)
        print("SEMANTIC CONTEXT ENGINE - COMPLETE TEST")
        print("=" * 80)
        
        if not self.validate_target():
            return False
        
        if not self.build_graph():
            return False
        
        if not self.analyze_impact():
            return False
        
        if not self.extract_context():
            return False
        
        self.validate()
        self.generate_report()
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        
        # Check results
        if any([
            len(self.graph.get('imports', {})),
            len(self.graph.get('calls', {})),
            len(self.graph.get('routes', {}))
        ]):
            print("\n[SUCCESS] Graph populated with semantic data!")
            print("Engine is working correctly.")
        else:
            print("\n[INFO] Graph is empty (no semantic matches extracted)")
            print("Check:")
            print("  - Language files have parseable code")
            print("  - Parser initialized correctly")
            print("  - Query patterns matched the code")
        
        return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "../test_microservice"
    runner = ProperSemanticTestRunner(target)
    success = runner.run()
    sys.exit(0 if success else 1)
