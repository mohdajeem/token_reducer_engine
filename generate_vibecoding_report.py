import os
import json
import time
from pathlib import Path

def resolve_investigation_size(repo_path, files_opened):
    if not files_opened:
        return 0
    chars = 0
    for f_open in files_opened:
        path_to_try = os.path.join(repo_path, f_open)
        if os.path.exists(path_to_try):
            try:
                with open(path_to_try, "r", encoding="utf-8") as f:
                    chars += len(f.read())
            except:
                pass
        else:
            basename = os.path.basename(f_open)
            for root, _, files in os.walk(repo_path):
                if basename in files:
                    try:
                        with open(os.path.join(root, basename), "r", encoding="utf-8") as f:
                            chars += len(f.read())
                            break
                    except:
                        pass
    return chars

def generate_report():
    project_root = Path(__file__).resolve().parent
    metrics_file = os.path.join(project_root, "snapshots", "vibecoding_metrics.json")
    report_file = os.path.join(project_root, "VIBECODING_REPORT.md")
    
    if not os.path.exists(metrics_file):
        # Create empty template if file does not exist
        os.makedirs(os.path.join(project_root, "snapshots"), exist_ok=True)
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        print(f"Created empty metrics snapshot database at: {metrics_file}")
        records = []
    else:
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            print(f"Error loading metrics: {e}")
            records = []
            
    if not records:
        print("No telemetry records found. Writing placeholder VIBECODING_REPORT.md")
        placeholder = (
            "# VibeCoding Productivity Report: Semantic Context Engine Impact\n\n"
            "No telemetry records registered yet. Start indexing and querying "
            "the MCP server to generate real-world productivity dashboards."
        )
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(placeholder)
        return

    # Calculate metrics
    total_queries = len(records)
    repos = {r.get("repository_path") for r in records if r.get("repository_path")}
    total_repos = len(repos)
    
    total_reduction_pct = 0.0
    total_selected_files = 0
    total_saved_repo_tokens = 0
    total_saved_investigation_tokens = 0
    investigations_tracked = 0
    
    largest_repo_path = "N/A"
    largest_repo_size = -1
    smallest_context_target = "N/A"
    smallest_context_size = float('inf')
    
    # Process each record and update fields
    updated_records = []
    for r in records:
        repo_path = r.get("repository_path", "")
        repo_chars = r.get("repository_character_count", 0)
        context_chars = r.get("context_character_count", 0)
        context_tokens = r.get("context_token_estimate", 0)
        target = r.get("target", "N/A")
        
        # Check largest repo
        if repo_chars > largest_repo_size:
            largest_repo_size = repo_chars
            largest_repo_path = repo_path
            
        # Check smallest context
        if context_chars < smallest_context_size:
            smallest_context_size = context_chars
            smallest_context_target = target
            
        # Dynamically calculate investigation size if files_opened_by_agent is provided
        files_opened = r.get("files_opened_by_agent")
        if files_opened and not r.get("investigation_character_count"):
            inv_chars = resolve_investigation_size(repo_path, files_opened)
            r["investigation_character_count"] = inv_chars
            r["investigation_token_estimate"] = inv_chars // 4
            
        inv_tokens = r.get("investigation_token_estimate")
        if inv_tokens is not None and inv_tokens > 0:
            saved_inv_tokens = max(0, inv_tokens - context_tokens)
            total_saved_investigation_tokens += saved_inv_tokens
            investigations_tracked += 1
            
        total_reduction_pct += r.get("reduction_percent_vs_repo", 0.0)
        total_selected_files += r.get("selected_file_count", 0)
        total_saved_repo_tokens += r.get("saved_tokens_vs_repo", 0)
        
        updated_records.append(r)
        
    # Save back updated records in case we filled in dynamic sizes
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(updated_records, f, indent=2)
        
    avg_reduction = total_reduction_pct / total_queries
    avg_selected = total_selected_files / total_queries
    
    # Build Markdown Report
    lines = [
        "# VibeCoding Productivity Report: Semantic Context Engine Impact",
        f"\n**Report Compiled on:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Tracked Sessions/Queries:** `{total_queries}`",
        f"**Active Codebases Indexed:** `{total_repos}`",
        "\n## 📊 VibeCoding Dashboard",
        "\n| Metric | Score / Value | Description |",
        "| :--- | :---: | :--- |",
        f"| **Total MCP Queries** | **{total_queries}** | Total context requests made by coding agents. |",
        f"| **Average Reduction Percentage** | **{avg_reduction:.2f}%** | Average codebase tokens pruned per request. |",
        f"| **Average Selected Files** | **{avg_selected:.1f}** | Average number of blast-radius files identified. |",
        f"| **Estimated Tokens Saved (vs Repo)** | **{total_saved_repo_tokens:,}** | Cumulative token savings vs sending entire repositories. |",
        f"| **Estimated Tokens Saved (vs Investigation)** | **{total_saved_investigation_tokens:,}** | Cumulative token savings vs manual files opened by agents. |",
        f"| **Largest Codebase Indexed** | `{os.path.basename(largest_repo_path)}` | size: `{largest_repo_size:,}` chars |",
        f"| **Smallest Context Returned** | `{smallest_context_target}` | size: `{smallest_context_size:,}` chars |",
        "\n---",
        "\n## 🔍 Telemetry Sessions Log",
        "\n| Timestamp | Target Spec | Traversal Policy | Files | Red. % | Saved Tokens | Agent Investigation |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :--- |"
    ]
    
    for r in updated_records:
        timestamp = r.get("timestamp", "").replace("T", " ").replace("Z", "")
        target = r.get("target", "N/A")
        policy = r.get("policy", "DEFAULT")
        files = r.get("selected_file_count", 0)
        red_pct = r.get("reduction_percent_vs_repo", 0.0)
        saved = r.get("saved_tokens_vs_repo", 0)
        
        inv_opened = r.get("files_opened_by_agent")
        if inv_opened:
            inv_str = f"Opened {len(inv_opened)} files (~{r.get('investigation_token_estimate', 0)} tokens)"
        else:
            inv_str = "*No manual trace*"
            
        lines.append(
            f"| {timestamp} | `{target}` | `{policy}` | {files} | {red_pct:.1f}% | {saved:,} | {inv_str} |"
        )
        
    report_content = "\n".join(lines)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"VibeCoding report successfully updated at: {report_file}")

if __name__ == "__main__":
    generate_report()
