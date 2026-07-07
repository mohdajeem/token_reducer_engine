import json
import os
from datetime import datetime

class SessionVsMcpAnalyzer:
    def __init__(self, metrics_path=r"snapshots/agent_session_metrics.json", vibecoding_path=r"snapshots/vibecoding_metrics.json"):
        self.metrics_path = metrics_path
        self.vibecoding_path = vibecoding_path

    def parse_iso_timestamp(self, ts_str):
        if not ts_str:
            return None
        # Normalize format (handle Z suffix)
        ts_clean = ts_str.replace("Z", "")
        # Try different datetime formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                pass
        return None

    def match_query_to_session(self, query_timestamp, sessions):
        query_time = self.parse_iso_timestamp(query_timestamp)
        if not query_time:
            return None
            
        for s_id, s_metrics in sessions.items():
            start_str = s_metrics.get("start_timestamp")
            end_str = s_metrics.get("end_timestamp")
            
            start_time = self.parse_iso_timestamp(start_str)
            end_time = self.parse_iso_timestamp(end_str)
            
            if start_time and end_time:
                if start_time <= query_time <= end_time:
                    return s_id
        return None

    def format_target_task(self, target, policy):
        # Human readable task formatting
        if target.startswith("ROUTE:"):
            parts = target.split(":")
            verb = parts[1].upper() if len(parts) > 1 else ""
            route = parts[2] if len(parts) > 2 else ""
            return f"Implement/Fix route: {verb} {route} ({policy})"
        return f"Task target: {target} ({policy})"

    def run_comparison(self):
        if not os.path.exists(self.metrics_path):
            raise FileNotFoundError(f"Agent session metrics file not found at {self.metrics_path}")
        if not os.path.exists(self.vibecoding_path):
            raise FileNotFoundError(f"Vibecoding telemetry file not found at {self.vibecoding_path}")
            
        with open(self.metrics_path, 'r', encoding='utf-8') as f:
            sessions = json.load(f)
            
        with open(self.vibecoding_path, 'r', encoding='utf-8') as f:
            mcp_queries = json.load(f)
            
        comparisons = []
        
        # Global Aggregates
        total_agent_tokens = 0
        total_mcp_tokens = 0
        total_tokens_saved = 0
        
        total_agent_files_set = set()
        total_mcp_files_set = set()
        
        for idx, query in enumerate(mcp_queries):
            ts = query.get("timestamp")
            matched_session_id = self.match_query_to_session(ts, sessions)
            
            # If no session matches strictly by timestamp interval, check fallback
            # E.g. matching closest session or just assigning to the main session in metrics
            if not matched_session_id and len(sessions) == 1:
                matched_session_id = list(sessions.keys())[0]
            elif not matched_session_id and len(sessions) > 0:
                # Fallback to matching by session_id in metadata if present, or assign to current session bec51ff1-...
                meta_session = query.get("agent_metadata", {}).get("session_id")
                if meta_session in sessions:
                    matched_session_id = meta_session
                else:
                    # Default to current session which represents the main telemetry
                    matched_session_id = "bec51ff1-e8b6-4e57-a51a-85b324af07d8"
                    
            if not matched_session_id:
                continue
                
            s_metrics = sessions[matched_session_id]
            
            # We define workspace code files = repo_tokens + external_tokens
            actual_agent_tokens = s_metrics.get("repo_tokens", 0) + s_metrics.get("external_tokens", 0)
            
            # Workspace code files opened count
            # Filters unique opened files keeping only repo and external files
            workspace_files = [p for p in s_metrics.get("unique_files_opened", []) 
                               if s_metrics.get("files_metadata", {}).get(p, {}).get("token_estimate", 0) > 0 
                               and not p.replace("\\", "/").lower().startswith("c:/users/ajeem/.gemini")]
            actual_agent_files = len(workspace_files)
            
            semantic_context_tokens = query.get("context_token_estimate", 0)
            selected_files = query.get("selected_files", [])
            semantic_context_files = len(selected_files)
            
            # Savings calculations
            token_savings_pct = (1.0 - (semantic_context_tokens / actual_agent_tokens)) * 100 if actual_agent_tokens else 0.0
            file_savings_pct = (1.0 - (semantic_context_files / actual_agent_files)) * 100 if actual_agent_files else 0.0
            
            comp = {
                "query_index": idx + 1,
                "timestamp": ts,
                "target": query.get("target"),
                "policy": query.get("policy"),
                "matched_session_id": matched_session_id,
                "actual_agent_tokens": actual_agent_tokens,
                "actual_agent_files": actual_agent_files,
                "semantic_context_tokens": semantic_context_tokens,
                "semantic_context_files": semantic_context_files,
                "token_savings_pct": token_savings_pct,
                "file_savings_pct": file_savings_pct,
                "selected_files": selected_files,
                "agent_files": workspace_files
            }
            comparisons.append(comp)
            
            # Accumulate unique files globally
            total_agent_files_set.update(workspace_files)
            total_mcp_files_set.update(selected_files)
            
            total_agent_tokens += actual_agent_tokens
            total_mcp_tokens += semantic_context_tokens
            
        total_tokens_saved = total_agent_tokens - total_mcp_tokens
        global_token_savings_pct = (total_tokens_saved / total_agent_tokens * 100) if total_agent_tokens else 0.0
        global_file_savings_pct = (1.0 - len(total_mcp_files_set) / len(total_agent_files_set)) * 100 if total_agent_files_set else 0.0
        
        report = {
            "queries_compared": comparisons,
            "aggregates": {
                "total_agent_tokens": total_agent_tokens,
                "total_mcp_tokens": total_mcp_tokens,
                "total_tokens_saved": total_tokens_saved,
                "global_token_savings_pct": global_token_savings_pct,
                "total_agent_files": len(total_agent_files_set),
                "total_mcp_files": len(total_mcp_files_set),
                "global_file_savings_pct": global_file_savings_pct
            }
        }
        return report

    def generate_markdown_report(self, report_data, output_report_path=r"SESSION_VS_MCP_REPORT.md"):
        lines = []
        lines.append("# Session Investigation vs. MCP Semantic Context Report")
        lines.append("\nThis report correlates the manual investigation telemetry of the Antigravity agent against the Semantic Context Engine's MCP query outputs.")
        
        lines.append("\n## Individual Task Comparisons")
        
        for comp in report_data["queries_compared"]:
            task_name = self.format_target_task(comp["target"], comp["policy"])
            lines.append(f"\n### Task: {task_name}")
            lines.append(f"- **Timestamp**: `{comp['timestamp']}`")
            lines.append(f"- **Matched Session**: `{comp['matched_session_id']}`")
            lines.append("\n**Agent Investigation**:")
            lines.append(f"- {comp['actual_agent_files']} unique code files")
            lines.append(f"- {comp['actual_agent_tokens']:,} investigation tokens")
            lines.append("\n**MCP Semantic Context**:")
            lines.append(f"- {comp['semantic_context_files']} selected code files")
            lines.append(f"- {comp['semantic_context_tokens']:,} semantic tokens")
            lines.append("\n**Reductions & Savings**:")
            lines.append(f"- **File Reduction**: {comp['file_savings_pct']:.1f}%")
            lines.append(f"- **Token Reduction**: {comp['token_savings_pct']:.1f}%")
            lines.append("\n---")
            
        agg = report_data["aggregates"]
        lines.append("\n## Aggregated Totals")
        lines.append("| Metric | Agent Baseline | MCP Semantic | Savings | Savings % |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        lines.append(f"| **Unique Code Files Touched** | {agg['total_agent_files']} | {agg['total_mcp_files']} | {agg['total_agent_files'] - agg['total_mcp_files']} | {agg['global_file_savings_pct']:.1f}% |")
        lines.append(f"| **Context Tokens Loaded** | {agg['total_agent_tokens']:,} | {agg['total_mcp_tokens']:,} | {agg['total_tokens_saved']:,} | {agg['global_token_savings_pct']:.1f}% |")
        
        lines.append(f"\n> [!TIP]\n> **Summary**: The Semantic Context Engine saved **{agg['total_tokens_saved']:,} tokens** across all session targets, yielding a **{agg['global_token_savings_pct']:.1f}% token reduction** compared to raw manual file investigations.")

        with open(output_report_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
            
        print(f"Generated comparison report at {output_report_path}")
