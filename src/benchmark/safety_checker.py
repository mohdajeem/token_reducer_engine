import os
import sys
from pathlib import Path

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent.parent))

from validation.patch_validator import PatchValidator
from validation.patch_simulator import PatchSimulator
from validation.patch_trust_analyzer import PatchTrustAnalyzer

class SafetyChecker:
    """
    Integrates the existing validation tools (PatchValidator, PatchSimulator, and PatchTrustAnalyzer)
    to check generated patches for AST errors, unresolved symbols, async violations, and taint flows.
    """
    @staticmethod
    def run_checks(sandbox_path: str, graph: dict, file_path: str, function_name: str, patch_content: str) -> dict:
        """
        Runs syntactic and semantic validation checks on the proposed patch.
        """
        patch_payload = {
            "file": file_path,
            "function": function_name or "GLOBAL_SCOPE",
            "patch": patch_content
        }
        
        # 1. Syntactic AST validation
        validator = PatchValidator(project_root=sandbox_path)
        syntax_res = validator.validate_patch(patch_payload)
        
        # 2. Semantic simulation checks
        simulator = PatchSimulator(graph=graph)
        sim_res = simulator.simulate(patch_payload)
        
        # 3. Security trust checks
        analyzer = PatchTrustAnalyzer(graph=graph)
        trust_res = analyzer.analyze(patch_payload)
        
        # Aggregate findings
        findings = []
        findings.extend(sim_res.get("findings", []))
        findings.extend(trust_res.get("findings", []))
        
        # Calculate overall safety
        trust_score = trust_res.get("trust_score", 1.0)
        sim_score = sim_res.get("simulation_score", 1.0)
        overall_score = min(trust_score, sim_score)
        
        return {
            "syntax_valid": syntax_res.get("valid", False),
            "syntax_reason": syntax_res.get("reason", ""),
            "safe_to_apply": syntax_res.get("valid", False) and sim_res.get("safe_to_apply", False) and trust_res.get("trusted", False),
            "trust_score": overall_score,
            "findings": findings,
            "semantics": sim_res.get("semantics", {})
        }
