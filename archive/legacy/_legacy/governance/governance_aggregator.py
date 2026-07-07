# ==========================================================
# GOVERNANCE AGGREGATOR
# ==========================================================


class GovernanceAggregator:

    # ======================================================
    # AGGREGATE
    # ======================================================

    def aggregate(

        self,

        semantic_validation,

        trust_analysis,

        confidence_result,

        intent_result,

        simulation_result,

        policy_result
    ):

        findings = []

        # ==================================================
        # COLLECT FINDINGS
        # ==================================================

        findings.extend(

            trust_analysis.get(
                "findings",
                []
            )
        )

        findings.extend(

            simulation_result.get(
                "findings",
                []
            )
        )

        # ==================================================
        # FINAL STATUS
        # ==================================================

        final_status = policy_result.get(
            "status",
            "UNKNOWN"
        )

        # ==================================================
        # RISK LEVEL
        # ==================================================

        risk_level = "LOW"

        confidence_score = confidence_result.get(

            "confidence_score",

            0.0
        )

        if confidence_score < 0.4:

            risk_level = "CRITICAL"

        elif confidence_score < 0.7:

            risk_level = "HIGH"

        elif confidence_score < 0.85:

            risk_level = "MEDIUM"

        # ==================================================
        # EXECUTABLE PATCH
        # ==================================================

        executable = intent_result.get(
            "executable",
            False
        )

        # ==================================================
        # SAFE APPLY
        # ==================================================

        safe_to_apply = (

            simulation_result.get(
                "safe_to_apply",
                False
            )

            and

            executable

            and

            final_status == "APPROVED"
        )

        # ==================================================
        # RECOMMENDED ACTION
        # ==================================================

        if final_status == "BLOCKED":

            action = (
                "Reject remediation"
            )

        elif final_status == "MANUAL_REVIEW":

            action = (
                "Require human approval"
            )

        elif not executable:

            action = (
                "Patch advisory only"
            )

        elif not safe_to_apply:

            action = (
                "Simulation risk detected"
            )

        else:

            action = (
                "Safe to auto-apply"
            )

        # ==================================================
        # GOVERNANCE SUMMARY
        # ==================================================

        summary = {

            "semantic_valid":
                semantic_validation.get(
                    "valid",
                    False
                ),

            "trust_score":
                trust_analysis.get(
                    "trust_score",
                    0.0
                ),

            "confidence_score":
                confidence_score,

            "intent":
                intent_result.get(
                    "intent"
                ),

            "simulation_score":
                simulation_result.get(
                    "simulation_score",
                    0.0
                ),

            "policy_status":
                final_status
        }

        # ==================================================
        # FINAL RESULT
        # ==================================================

        return {

            "final_status":
                final_status,

            "risk_level":
                risk_level,

            "safe_to_apply":
                safe_to_apply,

            "recommended_action":
                action,

            "governance_summary":
                summary,

            "findings":
                findings
        }