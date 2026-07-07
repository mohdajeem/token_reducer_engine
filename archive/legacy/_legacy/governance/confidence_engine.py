# ==========================================================
# CONFIDENCE ENGINE
# ==========================================================


class ConfidenceEngine:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        # ==================================================
        # WEIGHTS
        # ==================================================

        self.weights = {

            # ==============================================
            # POSITIVE
            # ==============================================

            "TRUSTED_SYMBOL":
                0.15,

            "SANITIZED_FLOW":
                0.10,

            "SEMANTIC_VALID":
                0.20,

            # ==============================================
            # NEGATIVE
            # ==============================================

            "UNKNOWN_FUNCTION":
                -0.25,

            "DANGEROUS_API":
                -0.60,

            "TAINT_REPROPAGATION":
                -0.75,

            "INVALID_SEMANTICS":
                -0.40
        }

    # ======================================================
    # CALCULATE CONFIDENCE
    # ======================================================

    def calculate(

        self,

        trust_result,

        semantic_validation
    ):

        score = 0.5

        reasoning = []

        # ==================================================
        # SEMANTIC VALIDATION
        # ==================================================

        if semantic_validation.get(

            "valid"
        ):

            score += self.weights[
                "SEMANTIC_VALID"
            ]

            reasoning.append({

                "type":
                    "SEMANTIC_VALID",

                "impact":
                    self.weights[
                        "SEMANTIC_VALID"
                    ],

                "message":
                    "Semantic validation passed"
            })

        else:

            score += self.weights[
                "INVALID_SEMANTICS"
            ]

            reasoning.append({

                "type":
                    "INVALID_SEMANTICS",

                "impact":
                    self.weights[
                        "INVALID_SEMANTICS"
                    ],

                "message":
                    "Semantic validation failed"
            })

        # ==================================================
        # TRUST FINDINGS
        # ==================================================

        for finding in trust_result.get(

            "findings",

            []
        ):

            finding_type = finding[
                "type"
            ]

            if (

                finding_type

                in

                self.weights
            ):

                impact = self.weights[
                    finding_type
                ]

                score += impact

                reasoning.append({

                    "type":
                        finding_type,

                    "impact":
                        impact,

                    "message":
                        finding.get(
                            "message"
                        )
                })

        # ==================================================
        # NORMALIZE
        # ==================================================

        score = max(
            0.0,
            min(1.0, score)
        )

        # ==================================================
        # FINAL DECISION
        # ==================================================

        approved = score >= 0.7

        return {

            "confidence_score":
                round(score, 2),

            "approved":
                approved,

            "reasoning":
                reasoning
        }