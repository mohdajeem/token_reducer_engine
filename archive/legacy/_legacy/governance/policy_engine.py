# ==========================================================
# POLICY ENGINE
# ==========================================================


class PolicyEngine:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        # ==================================================
        # CONFIG
        # ==================================================

        self.minimum_confidence = 0.70

        self.blocking_findings = {

            "DANGEROUS_API",

            "TAINT_REPROPAGATION"
        }

        self.manual_review_findings = {

            "UNKNOWN_FUNCTION"
        }

    # ======================================================
    # EVALUATE
    # ======================================================

    def evaluate(

        self,

        confidence_result,

        trust_result
    ):

        confidence_score = confidence_result.get(

            "confidence_score",

            0.0
        )

        findings = trust_result.get(

            "findings",

            []
        )

        decisions = []

        blocked = False

        manual_review = False

        # ==================================================
        # BLOCKING POLICIES
        # ==================================================

        for finding in findings:

            finding_type = finding.get(
                "type"
            )

            # ==============================================
            # BLOCK IMMEDIATELY
            # ==============================================

            if (

                finding_type

                in

                self.blocking_findings
            ):

                blocked = True

                decisions.append({

                    "decision":
                        "BLOCK",

                    "reason":
                        finding.get(
                            "message"
                        ),

                    "finding":
                        finding_type
                })

            # ==============================================
            # REQUIRE MANUAL REVIEW
            # ==============================================

            elif (

                finding_type

                in

                self.manual_review_findings
            ):

                manual_review = True

                decisions.append({

                    "decision":
                        "MANUAL_REVIEW",

                    "reason":
                        finding.get(
                            "message"
                        ),

                    "finding":
                        finding_type
                })

        # ==================================================
        # LOW CONFIDENCE POLICY
        # ==================================================

        if (

            confidence_score

            <

            self.minimum_confidence
        ):

            manual_review = True

            decisions.append({

                "decision":
                    "LOW_CONFIDENCE",

                "reason":
                    f"Confidence score "
                    f"{confidence_score} "
                    f"below threshold "
                    f"{self.minimum_confidence}"
            })

        # ==================================================
        # FINAL STATUS
        # ==================================================

        if blocked:

            final_status = "BLOCKED"

        elif manual_review:

            final_status = "MANUAL_REVIEW"

        else:

            final_status = "APPROVED"

            decisions.append({

                "decision":
                    "APPROVED",

                "reason":
                    "Patch satisfies governance policies"
            })

        # ==================================================
        # FINAL RESULT
        # ==================================================

        return {

            "status":
                final_status,

            "confidence_score":
                confidence_score,

            "decisions":
                decisions
        }