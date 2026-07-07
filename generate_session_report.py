import json
import os
import sys

# Ensure project src path is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from telemetry.agent_session_analyzer import AgentSessionAnalyzer
from telemetry.session_vs_mcp_analyzer import SessionVsMcpAnalyzer

def generate_report():
    brain_dir = r"C:\Users\ajeem\.gemini\antigravity-ide\brain"
    session_ids = [
        "bec51ff1-e8b6-4e57-a51a-85b324af07d8",
        "bdbdb9aa-f8f9-4b1f-b37b-4f034d1caa78"
    ]
    
    # 1. Run Session Analyzer (V2)
    print("Stage 1: Running Agent Session Analyzer V2...")
    analyzer = AgentSessionAnalyzer(brain_dir=brain_dir)
    all_metrics = analyzer.run_and_save(session_ids, output_path="snapshots/agent_session_metrics.json")
    
    # 2. Formulate AGENT_SESSION_REPORT.md
    report_content = []
    report_content.append("# Antigravity Agent Session Telemetry Report (V2)")
    report_content.append("\nThis report analyzes the investigation and modification effort of the Antigravity coding agent across multiple sessions, separating tokens by workspace, system, and external paths.")
    
    for s_id in session_ids:
        if s_id not in all_metrics:
            continue
            
        metrics = all_metrics[s_id]
        unique_opened = metrics["unique_files_opened"]
        unique_modified = metrics["unique_files_modified"]
        metadata = metrics["files_metadata"]
        frequencies = metrics["open_frequencies"]
        
        # Calculate largest file opened
        largest_file = None
        largest_chars = -1
        for fpath, meta in metadata.items():
            if meta["character_count"] > largest_chars:
                largest_chars = meta["character_count"]
                largest_file = fpath
                
        # Calculate most frequently opened file
        most_freq_file = None
        max_freq = -1
        for fpath, freq in frequencies.items():
            if freq > max_freq:
                max_freq = freq
                most_freq_file = fpath
                
        # Confidence calculation
        disk_present_count = sum(1 for fpath in unique_opened if os.path.exists(fpath))
        confidence_pct = (disk_present_count / len(unique_opened) * 100) if unique_opened else 100.0
        
        # Abbreviate path
        def abbreviate_path(p):
            p_norm = p.replace("\\", "/")
            workspace_root = "c:/Users/ajeem/Downloads/downloads/CoderReviewAgent2/token_reducer_system"
            if p_norm.lower().startswith(workspace_root.lower()):
                return f"repo://{p_norm[len(workspace_root):].lstrip('/')}"
            
            gemini_root = "c:/users/ajeem/.gemini/antigravity-ide"
            if p_norm.lower().startswith(gemini_root.lower()):
                return f"gemini://{p_norm[len(gemini_root):].lstrip('/')}"
                
            testing_root = "c:/users/ajeem/downloads/downloads/testing/testing1"
            if p_norm.lower().startswith(testing_root.lower()):
                return f"external://testing1/{p_norm[len(testing_root):].lstrip('/')}"
                
            return p_norm

        report_content.append(f"\n## Session: `{s_id}`")
        report_content.append("\n### Overview & Session Metrics")
        
        report_content.append("| Metric | Value |")
        report_content.append("| :--- | :--- |")
        report_content.append(f"| **Session ID** | `{s_id}` |")
        report_content.append(f"| **Files Opened (Unique)** | {metrics['files_opened_count']} |")
        report_content.append(f"| **Files Modified (Unique)** | {metrics['files_modified_count']} |")
        report_content.append(f"| **Total Investigation Characters** | {metrics['investigation_character_count']:,} |")
        report_content.append(f"| **Total Investigation Tokens** | {metrics['investigation_token_estimate']:,} |")
        report_content.append(f"| **Repo Code Tokens (`repo://`)** | {metrics['repo_tokens']:,} |")
        report_content.append(f"| **External Code Tokens (`external://`)** | {metrics['external_tokens']:,} |")
        report_content.append(f"| **System/Log Tokens (`gemini://`)** | {metrics['gemini_tokens']:,} |")
        report_content.append(f"| **Confidence Level** | {confidence_pct:.1f}% ({disk_present_count}/{len(unique_opened)} files on disk) |")
        
        report_content.append("\n### Key Highlights")
        if largest_file:
            report_content.append(f"- **Largest File Opened**: `{abbreviate_path(largest_file)}` ({largest_chars:,} chars, {metadata[largest_file]['token_estimate']:,} tokens)")
        if most_freq_file:
            report_content.append(f"- **Most Frequently Opened File**: `{abbreviate_path(most_freq_file)}` (opened {max_freq} times)")
            
        report_content.append("\n### Files Opened (Unique)")
        report_content.append("| File Path | Read Frequency | Character Count | Token Estimate | Category |")
        report_content.append("| :--- | :---: | :---: | :---: | :---: |")
        for fpath in unique_opened:
            meta = metadata[fpath]
            freq = frequencies.get(fpath, 0)
            cat = analyzer.categorize_path(fpath).upper()
            report_content.append(f"| `{abbreviate_path(fpath)}` | {freq} | {meta['character_count']:,} | {meta['token_estimate']:,} | {cat} |")
            
        report_content.append("\n### Files Modified (Unique)")
        if unique_modified:
            for fpath in unique_modified:
                report_content.append(f"- `{abbreviate_path(fpath)}`")
        else:
            report_content.append("*No files were modified in this session.*")
            
        report_content.append("\n### Top 20 Opened Files by Read Frequency")
        report_content.append("| Rank | File Path | Read Frequency | Character Count | Token Estimate |")
        report_content.append("| :---: | :--- | :---: | :---: | :---: |")
        sorted_by_freq = sorted(frequencies.items(), key=lambda x: (-x[1], x[0]))
        for idx, (fpath, freq) in enumerate(sorted_by_freq[:20]):
            meta = metadata[fpath]
            report_content.append(f"| {idx+1} | `{abbreviate_path(fpath)}` | {freq} | {meta['character_count']:,} | {meta['token_estimate']:,} |")

        report_content.append("\n### Raw Transcript Evidence")
        log_path = os.path.join(brain_dir, s_id, ".system_generated", "logs", "transcript.jsonl")
        step_count = 0
        tool_counts = {}
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as lf:
                for l in lf:
                    try:
                        step_data = json.loads(l)
                        step_count += 1
                        for tc in step_data.get("tool_calls", []):
                            tname = tc.get("name")
                            if tname:
                                tool_counts[tname] = tool_counts.get(tname, 0) + 1
                    except:
                        pass
        report_content.append(f"- **Total Transcript Steps Audited**: {step_count} steps.")
        report_content.append("- **Parsed Tool Invocations**:")
        for tname, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            report_content.append(f"  - `{tname}`: {count} invocations")
            
        report_content.append("\n---")
        
    with open("AGENT_SESSION_REPORT.md", 'w', encoding='utf-8') as rf:
        rf.write("\n".join(report_content))
    print("Generated AGENT_SESSION_REPORT.md")
    
    # 3. Run Session vs MCP Comparison Analyzer
    print("\nStage 2: Running Session vs MCP Analyzer...")
    comparison_analyzer = SessionVsMcpAnalyzer(
        metrics_path="snapshots/agent_session_metrics.json",
        vibecoding_path="snapshots/vibecoding_metrics.json"
    )
    report_data = comparison_analyzer.run_comparison()
    comparison_analyzer.generate_markdown_report(report_data, "SESSION_VS_MCP_REPORT.md")

if __name__ == "__main__":
    generate_report()
