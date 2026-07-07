# ==========================================================
# GOVERNANCE PIPELINE TEST
# ==========================================================

from ai_reviewer.fixes.patch_trust_analyzer import (
    PatchTrustAnalyzer
)

from ai_reviewer.fixes.confidence_engine import (
    ConfidenceEngine
)

from ai_reviewer.fixes.policy_engine import (
    PolicyEngine
)

from ai_reviewer.fixes.patch_intent_classifier import (
    PatchIntentClassifier
)

from ai_reviewer.fixes.patch_simulator import (
    PatchSimulator
)

from ai_reviewer.fixes.governance_aggregator import (
    GovernanceAggregator
)

from ai_reviewer.fixes.semantic_validator import (
    SemanticValidator
)

from semantic.semantic_graph import (
    SemanticGraph
)


# ==========================================================
# RUN TEST
# ==========================================================

def run_governance_test(

    graph
):

    print("\n")
    print("=" * 80)
    print("🔥 GOVERNANCE PIPELINE TEST")
    print("=" * 80)

    # ======================================================
    # SAMPLE PATCH
    # ======================================================

    sample_patch = {

        "file":
            "services/userService.js",

        "function":
            "fetchUsers",

        "patch":
            """
+ const hashedPassword = hashPassword(password)
+ return bcrypt.hash(hashedPassword)
            """
    }

    # ======================================================
    # SEMANTIC VALIDATOR
    # ======================================================

    semantic_validator = (
        SemanticValidator(
            graph
        )
    )

    semantic_result = (

        semantic_validator
        .validate_patch_semantics(
            sample_patch
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 SEMANTIC VALIDATION")
    print("=" * 80)

    print(semantic_result)

    # ======================================================
    # TRUST ANALYZER
    # ======================================================

    trust_analyzer = (
        PatchTrustAnalyzer(
            graph
        )
    )

    trust_result = (
        trust_analyzer.analyze(
            sample_patch
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 PATCH TRUST ANALYZER")
    print("=" * 80)

    print(trust_result)

    # ======================================================
    # CONFIDENCE ENGINE
    # ======================================================

    confidence_engine = (
        ConfidenceEngine()
    )

    confidence_result = (

        confidence_engine.calculate(

            trust_result,

            semantic_result
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 CONFIDENCE ENGINE")
    print("=" * 80)

    print(confidence_result)

    # ======================================================
    # POLICY ENGINE
    # ======================================================

    policy_engine = (
        PolicyEngine()
    )

    policy_result = (

        policy_engine.evaluate(

            confidence_result,

            trust_result
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 POLICY ENGINE")
    print("=" * 80)

    print(policy_result)

    # ======================================================
    # PATCH INTENT
    # ======================================================

    classifier = (
        PatchIntentClassifier()
    )

    intent_result = (
        classifier.classify(
            sample_patch
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 PATCH INTENT CLASSIFIER")
    print("=" * 80)

    print(intent_result)

    # ======================================================
    # PATCH SIMULATOR
    # ======================================================

    simulator = (
        PatchSimulator(
            graph
        )
    )

    simulation_result = (
        simulator.simulate(
            sample_patch
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 PATCH SIMULATOR")
    print("=" * 80)

    print(simulation_result)

    # ======================================================
    # GOVERNANCE AGGREGATOR
    # ======================================================

    aggregator = (
        GovernanceAggregator()
    )

    governance_result = (

        aggregator.aggregate(

            semantic_validation=
                semantic_result,

            trust_analysis=
                trust_result,

            confidence_result=
                confidence_result,

            intent_result=
                intent_result,

            simulation_result=
                simulation_result,

            policy_result=
                policy_result
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 GOVERNANCE AGGREGATOR")
    print("=" * 80)

    print(governance_result)

    return governance_result