class ScoringEngine:
    """
    Computes all standard scoring metrics for benchmark tasks:
    - Edit Recall
    - Edit Precision
    - Context Efficiency
    - Hallucination Rate
    - Test Pass Rate
    - Cost (USD)
    """
    @staticmethod
    def compute_metrics(
        selected_files: list,
        ground_truth_files: list,
        context_char_size: int,
        total_repo_chars: int,
        safety_results: dict,
        test_passed: bool,
        input_tokens: int,
        output_tokens: int,
        model_provider: str,
        latency: float
    ) -> dict:
        # Normalize file paths to forward slashes for reliable matching
        norm_selected = {f.replace("\\", "/").strip() for f in selected_files}
        norm_ground = {f.replace("\\", "/").strip() for f in ground_truth_files}
        
        # 1. Recall & Precision
        tp = norm_selected.intersection(norm_ground)
        recall = len(tp) / len(norm_ground) if norm_ground else 1.0
        precision = len(tp) / len(norm_selected) if norm_selected else 0.0
        
        # 2. Context Efficiency
        efficiency = (1.0 - (context_char_size / total_repo_chars)) * 100.0 if total_repo_chars > 0 else 0.0
        efficiency = max(0.0, min(100.0, efficiency))
        
        # 3. Hallucination Rate
        # Count unresolved function calls / variables introduced by the patch
        findings = safety_results.get("findings", [])
        hallucination_findings = sum(
            1 for f in findings 
            if f.get("type") in ("UNRESOLVED_CALL", "UNKNOWN_FUNCTION", "NEW_VARIABLE")
        )
        # Ratio relative to called functions in the patch (default to 1 to avoid DivisionByZero)
        semantics = safety_results.get("semantics", {})
        called_count = len(semantics.get("called_functions", []))
        hallucination_rate = (hallucination_findings / max(1, called_count)) * 100.0
        
        # 4. Test Pass Rate
        test_pass_rate = 1.0 if test_passed else 0.0
        
        # 5. Cost calculation (based on typical API prices per 1M tokens)
        pricing = {
            "openai": {"input": 5.0 / 1e6, "output": 15.0 / 1e6},
            "claude": {"input": 3.0 / 1e6, "output": 15.0 / 1e6},
            "gemini": {"input": 1.25 / 1e6, "output": 3.75 / 1e6},
            "mock": {"input": 0.0, "output": 0.0}
        }
        
        provider = model_provider.lower()
        if "openai" in provider:
            rate = pricing["openai"]
        elif "claude" in provider or "anthropic" in provider:
            rate = pricing["claude"]
        elif "gemini" in provider or "google" in provider:
            rate = pricing["gemini"]
        else:
            rate = pricing["mock"]
            
        cost = (input_tokens * rate["input"]) + (output_tokens * rate["output"])
        
        return {
            "edit_recall": round(recall, 4),
            "edit_precision": round(precision, 4),
            "context_efficiency": round(efficiency, 2),
            "hallucination_rate": round(hallucination_rate, 2),
            "test_pass_rate": test_pass_rate,
            "cost_usd": round(cost, 6),
            "latency_seconds": round(latency, 2)
        }
