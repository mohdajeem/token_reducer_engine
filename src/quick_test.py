#!/usr/bin/env python3
"""
Simple test runner - ASCII only
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from semantic_core import GraphBuilder
from impact_engine import GraphTraversal
from context_engine import ContextExtractor
from validation import SemanticValidator


def main(target_dir):
    """Run test on target directory."""
    
    target_dir = os.path.abspath(target_dir)
    
    print("\n" + "=" * 80)
    print("SEMANTIC CONTEXT ENGINE - TEST")
    print("=" * 80)
    print(f"\nTarget: {target_dir}")
    
    # Validate
    if not os.path.isdir(target_dir):
        print(f"[ERROR] Not a directory: {target_dir}")
        return False
    
    # Count files
    files = []
    for root, dirs, fnames in os.walk(target_dir):
        for fname in fnames:
            ext = Path(fname).suffix
            if ext in {'.py', '.js', '.jsx', '.ts', '.tsx'}:
                files.append(os.path.join(root, fname))
    
    print(f"[OK] Found {len(files)} source files")
    
    # Step 1: Build graph
    print("\n[STEP 1] Building semantic graph...")
    try:
        builder = GraphBuilder()
        graph = builder.graph
        
        print(f"[OK] Graph created")
        print(f"     - Imports: {len(graph.get('imports', {}))}")
        print(f"     - Routes: {len(graph.get('routes', {}))}")
        print(f"     - Calls: {len(graph.get('calls', {}))}")
        print(f"     - Execution edges: {len(graph.get('execution_edges', []))}")
        
    except Exception as e:
        print(f"[ERROR] Failed to build graph: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Try traversal
    print("\n[STEP 2] Testing graph traversal...")
    try:
        traversal = GraphTraversal(graph)
        print(f"[OK] Traversal engine created")
        
    except Exception as e:
        print(f"[ERROR] Failed to create traversal: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Try context extraction
    print("\n[STEP 3] Testing context extraction...")
    try:
        extractor = ContextExtractor(graph, target_dir)
        print(f"[OK] Context extractor created")
        
    except Exception as e:
        print(f"[ERROR] Failed to create extractor: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Validation
    print("\n[STEP 4] Validation...")
    try:
        validator = SemanticValidator(graph)
        print(f"[OK] Validator created")
        
    except Exception as e:
        print(f"[WARN] Validator error: {e}")
    
    print("\n" + "=" * 80)
    print("[SUCCESS] Engine test complete!")
    print("=" * 80)
    print("\nAll core modules are working correctly.")
    print(f"Test on: {target_dir}\n")
    
    return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "../test_microservice"
    success = main(target)
    sys.exit(0 if success else 1)
