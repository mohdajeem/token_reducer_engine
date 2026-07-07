import os
import json
import subprocess
import sys
from pathlib import Path

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent / 'src'))

from api.mcp_server import mcp_build_graph, mcp_query_context

def main():
    repo_path = r"C:\Users\ajeem\Downloads\downloads\testing\testing1"
    
    print("=== VERIFYING TELEMETRY SYSTEM ===")
    
    # 1. Rebuild graph and trigger query contexts
    print("  Triggering mcp_build_graph...")
    mcp_build_graph(repo_path, force_rebuild=True)
    
    print("  Triggering mcp_query_context for login route...")
    mcp_query_context("ROUTE:post:/login", "NEW_FEATURE")
    
    print("  Triggering mcp_query_context for register route...")
    mcp_query_context("ROUTE:post:/register", "NEW_FEATURE")
    
    # 2. Check snapshots/vibecoding_metrics.json
    metrics_path = os.path.join(current_file.parent, "snapshots", "vibecoding_metrics.json")
    if not os.path.exists(metrics_path):
        print("  [ERROR] snapshots/vibecoding_metrics.json was not created.")
        sys.exit(1)
        
    with open(metrics_path, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    print(f"  Successfully found {len(records)} records logged in snapshots/vibecoding_metrics.json.")
    
    # 3. Simulate Agent Investigation Mode on the first record
    print("  Simulating Agent Investigation Mode on the first record...")
    records[0]["files_opened_by_agent"] = [
        "src/routes/auth.routes.js",
        "src/services/auth.service.js",
        "src/controllers/auth.controller.js"
    ]
    
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
        
    # 4. Generate report
    print("  Running generate_vibecoding_report.py...")
    import generate_vibecoding_report
    generate_vibecoding_report.generate_report()
    
    # 5. Check output report
    report_path = os.path.join(current_file.parent, "VIBECODING_REPORT.md")
    if os.path.exists(report_path):
        print(f"  [SUCCESS] VIBECODING_REPORT.md generated successfully at: {report_path}")
        # View report header
        with open(report_path, "r", encoding="utf-8") as f:
            print("\n--- REPORT HEADER PREVIEW ---")
            lines = f.readlines()
            for line in lines[:20]:
                safe_line = line.rstrip().encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
                print(safe_line)
            print("-----------------------------\n")
    else:
        print("  [ERROR] VIBECODING_REPORT.md not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
