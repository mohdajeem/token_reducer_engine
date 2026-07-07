# ==========================================================
# SEMANTIC API SERVER
# ==========================================================
# Query interface for external AI agents.
#
# This is how Copilot, Claude, Cursor, Cline, and other
# AI agents consume the semantic intelligence.

from typing import Dict, Any, Optional
import json
from dataclasses import dataclass


@dataclass
class ImpactRequest:
    """Request to analyze impact of a change."""
    file: str
    line: int
    function: Optional[str] = None


@dataclass
class ContextRequest:
    """Request to extract semantic context."""
    file: str
    line: int
    token_budget: Optional[int] = 2000


@dataclass
class ValidateRequest:
    """Request to validate a patch."""
    file: str
    function: str
    patch: str


@dataclass
class RebuildRequest:
    """Request to rebuild graph."""
    incremental: bool = True
    target_files: Optional[list] = None


# ==========================================================
# RESPONSE MODELS
# ==========================================================

class ImpactResponse:
    """Response containing impact analysis."""
    
    def __init__(self, impact_data: Dict[str, Any]):
        self.upstream_functions = impact_data.get("upstream", [])
        self.downstream_functions = impact_data.get("downstream", [])
        self.affected_routes = impact_data.get("routes", [])
        self.affected_contracts = impact_data.get("contracts", [])
        self.risk_level = impact_data.get("risk", "UNKNOWN")
    
    def to_dict(self):
        return {
            "upstream_functions": self.upstream_functions,
            "downstream_functions": self.downstream_functions,
            "affected_routes": self.affected_routes,
            "affected_contracts": self.affected_contracts,
            "risk_level": self.risk_level
        }


class ContextResponse:
    """Response containing semantic context payload."""
    
    def __init__(self, context_data: Dict[str, Any]):
        self.changed_file = context_data.get("changed_file")
        self.changed_function = context_data.get("changed_function")
        self.impacted_functions = context_data.get("impacted_functions", [])
        self.affected_routes = context_data.get("affected_routes", [])
        self.relevant_code = context_data.get("relevant_code", {})
        self.risk_level = context_data.get("risk_level", "UNKNOWN")
        self.token_estimate = context_data.get("token_estimate", 0)
    
    def to_dict(self):
        return {
            "changed_file": self.changed_file,
            "changed_function": self.changed_function,
            "impacted_functions": self.impacted_functions,
            "affected_routes": self.affected_routes,
            "relevant_code": self.relevant_code,
            "risk_level": self.risk_level,
            "token_estimate": self.token_estimate
        }


class ValidationResponse:
    """Response containing validation result."""
    
    def __init__(self, valid: bool, reason: str = "", findings: list = None):
        self.valid = valid
        self.reason = reason
        self.findings = findings or []
    
    def to_dict(self):
        return {
            "valid": self.valid,
            "reason": self.reason,
            "findings": self.findings
        }


# ==========================================================
# SEMANTIC API HANDLER
# ==========================================================

class SemanticAPIHandler:
    """
    Core API handler for semantic queries.
    
    This is independent of HTTP framework (Flask/FastAPI).
    It can be wrapped by any HTTP server.
    """
    
    def __init__(self, graph=None, project_root: str = "."):
        """
        Initialize handler with semantic graph.
        
        Args:
            graph: The semantic graph (dict)
            project_root: Root directory of project
        """
        self.graph = graph or {}
        self.project_root = project_root
    
    def handle_impact(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle impact analysis request."""
        try:
            from impact_engine import GraphTraversal
            
            file_path = request.get("file")
            line = request.get("line")
            function = request.get("function")
            
            if not file_path:
                return {
                    "error": "Missing 'file' parameter"
                }
            
            target = {
                "type": "FUNCTION",
                "file": file_path,
                "function": function or "GLOBAL_SCOPE"
            }
            
            traversal = GraphTraversal(self.graph)
            upstream = traversal.find_upstream_nodes(target)
            
            response = ImpactResponse({
                "upstream": upstream,
                "risk": "HIGH" if len(upstream) > 5 else "MEDIUM"
            })
            
            return response.to_dict()
            
        except Exception as e:
            return {"error": str(e)}
    
    def handle_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle context extraction request."""
        try:
            from context_engine import ContextExtractor
            
            file_path = request.get("file")
            line = request.get("line")
            token_budget = request.get("token_budget", 2000)
            
            if not file_path:
                return {
                    "error": "Missing 'file' parameter"
                }
            
            # Get impact first
            impact_result = self.handle_impact({
                "file": file_path,
                "line": line
            })
            
            if "error" in impact_result:
                return impact_result
            
            # Extract context
            extractor = ContextExtractor(self.graph, self.project_root)
            context = extractor.extract_context(impact_result)
            
            response = ContextResponse({
                "changed_file": file_path,
                "impacted_functions": context.get("relevant_functions", []),
                "affected_routes": context.get("route_context", []),
                "relevant_code": context.get("code_snippets", []),
                "token_estimate": min(len(str(context)) // 4, token_budget)
            })
            
            return response.to_dict()
            
        except Exception as e:
            return {"error": str(e)}
    
    def handle_validate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patch validation request."""
        try:
            from validation import PatchValidator, SemanticValidator
            
            file_path = request.get("file")
            patch = request.get("patch")
            
            if not file_path or not patch:
                return {
                    "error": "Missing 'file' or 'patch' parameter"
                }
            
            # Syntax validation
            validator = PatchValidator(self.project_root)
            patch_obj = {
                "file": file_path,
                "patch": patch
            }
            
            syntax_check = validator.validate_patch(patch_obj)
            
            if not syntax_check.get("valid"):
                response = ValidationResponse(
                    valid=False,
                    reason=syntax_check.get("reason", "Invalid patch")
                )
                return response.to_dict()
            
            # Semantic validation
            sem_validator = SemanticValidator(self.graph)
            semantic_check = sem_validator.validate_patch(patch_obj)
            
            response = ValidationResponse(
                valid=semantic_check.get("valid", True),
                reason=semantic_check.get("reason", ""),
                findings=semantic_check.get("findings", [])
            )
            
            return response.to_dict()
            
        except Exception as e:
            return {"error": str(e)}
    
    def handle_rebuild(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graph rebuild request."""
        try:
            from incremental_runtime import ChangeDetector
            
            incremental = request.get("incremental", True)
            target_files = request.get("target_files", [])
            
            if incremental:
                detector = ChangeDetector()
                diff = detector.get_git_diff()
                changes = detector.extract_changes(diff)
                
                return {
                    "status": "rebuilt_incrementally",
                    "changed_files": changes,
                    "message": f"Updated {len(changes)} files"
                }
            else:
                # Full rebuild would go here
                return {
                    "status": "full_rebuild",
                    "message": "Full graph rebuild triggered"
                }
            
        except Exception as e:
            return {"error": str(e)}


# ==========================================================
# FLASK WRAPPER (OPTIONAL)
# ==========================================================

def create_flask_api(graph=None, project_root: str = "."):
    """
    Create Flask API server for semantic queries.
    
    Usage:
        app = create_flask_api()
        app.run(port=5000)
    """
    try:
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        handler = SemanticAPIHandler(graph, project_root)
        
        @app.route("/impact", methods=["POST"])
        def impact():
            data = request.get_json()
            result = handler.handle_impact(data)
            return jsonify(result)
        
        @app.route("/context", methods=["POST"])
        def context():
            data = request.get_json()
            result = handler.handle_context(data)
            return jsonify(result)
        
        @app.route("/validate", methods=["POST"])
        def validate():
            data = request.get_json()
            result = handler.handle_validate(data)
            return jsonify(result)
        
        @app.route("/rebuild", methods=["POST"])
        def rebuild():
            data = request.get_json()
            result = handler.handle_rebuild(data)
            return jsonify(result)
        
        @app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok"})
        
        return app
        
    except ImportError:
        raise ImportError("Flask is required for API server. Install with: pip install flask")


if __name__ == "__main__":
    app = create_flask_api()
    print("🚀 Semantic API Server starting on http://localhost:5000")
    app.run(debug=True, port=5000)
