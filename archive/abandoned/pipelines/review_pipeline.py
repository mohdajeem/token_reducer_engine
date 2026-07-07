# ==========================================================
# REVIEW PIPELINE
# ==========================================================

import json

from ai_reviewer.orchestrator.review_orchestrator import (
    ReviewOrchestrator
)

from ai_reviewer.fixes.fix_generator import (
    FixGenerator
)

from ai_reviewer.reviewers.reviewer_factory import (
    ReviewerFactory
)

from config.settings import (
    AI_PROVIDER
)

from ai_reviewer.fixes.patch_validator import (
    PatchValidator
)
from ai_reviewer.fixes.semantic_validator import (
    SemanticValidator
)

from ai_reviewer.fixes.patch_trust_analyzer import (
    PatchTrustAnalyzer
)

from ai_reviewer.fixes.confidence_engine import (
    ConfidenceEngine
)

from ai_reviewer.fixes.policy_engine import (
    PolicyEngine
)


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

from ai_reviewer.reporting.governance_report_builder import (
    GovernanceReportBuilder
)


# ==========================================================
# RUN REVIEW PIPELINE
# ==========================================================

def run_review_pipeline(

    graph,

    project_root,

    function_index,

    provider=AI_PROVIDER
    # provider="groq"
):

    print("\n")
    print("=" * 80)
    print("🔥 AUTONOMOUS REVIEW PIPELINE")
    print("=" * 80)

    # ======================================================
    # ORCHESTRATOR
    # ======================================================

    orchestrator = ReviewOrchestrator(

        graph=graph,

        project_root=project_root,

        function_index=function_index,

        provider=provider
    )

    results = orchestrator.run()

    # ======================================================
    # FINAL RESULTS
    # ======================================================

    print("\n")
    print("=" * 80)
    print("🔥 FINAL REVIEW RESULTS")
    print("=" * 80)

    print(
        json.dumps(
            results,
            indent=2
        )
    )

    # ======================================================
    # NO RESULTS
    # ======================================================

    if not results:

        return []

    # ======================================================
    # FIX GENERATION
    # ======================================================

    print("\n")
    print("=" * 80)
    print("🔥 FIX GENERATION")
    print("=" * 80)

    reviewer = ReviewerFactory.create(
        provider
    )

    fix_generator = FixGenerator(
        reviewer
    )

    # ======================================================
    # FIRST REVIEW RESULT
    # ======================================================

    first_result = results[0]

    fixes = (
        fix_generator.generate_fixes(

            review_results=
                first_result["reviews"],

            context_result=
                first_result["context"],

            changes=
                orchestrator.latest_changes
        )
    )

    print(

        json.dumps(

            fixes,

            indent=2
        )
    )

    # ======================================================
    # PATCH VALIDATION
    # ======================================================

    print("\n")
    print("=" * 80)
    print("🔥 PATCH VALIDATION")
    print("=" * 80)

    validator = PatchValidator(
        project_root
    )

    validation_results = []

    semantic_validator = (
        SemanticValidator(
            graph
        )
    )

    # ======================================================
    # GOVERNANCE RUNTIME
    # ======================================================

    trust_analyzer = (
        PatchTrustAnalyzer(
            graph
        )
    )

    confidence_engine = (
        ConfidenceEngine()
    )

    policy_engine = (
        PolicyEngine()
    )

    intent_classifier = (
        PatchIntentClassifier()
    )

    patch_simulator = (
        PatchSimulator(
            graph
        )
    )

    governance_aggregator = (
        GovernanceAggregator()
    )

    trust_analyzer = (
        PatchTrustAnalyzer(
            graph
        )
    )

    confidence_engine = (
        ConfidenceEngine()
    )

    policy_engine = (
        PolicyEngine()
    )

    for patch in fixes:

        result = (
            validator.validate_patch(
                patch
            )
        )

        semantic_result = (

            semantic_validator
            .validate_patch_semantics(
                patch
            )
        )

        # ==============================================
        # TRUST ANALYSIS
        # ==============================================

        trust_result = (

            trust_analyzer.analyze(
                patch
            )
        )

        # ==============================================
        # CONFIDENCE ENGINE
        # ==============================================

        confidence_result = (

            confidence_engine.calculate(

                trust_result,

                semantic_result
            )
        )

        # ==============================================
        # POLICY ENGINE
        # ==============================================

        policy_result = (

            policy_engine.evaluate(

                confidence_result,

                trust_result
            )
        )
        
        
        # ==============================================
        # TRUST ANALYSIS
        # ==============================================

        trust_result = (

            trust_analyzer.analyze(
                patch
            )
        )

        # ==============================================
        # CONFIDENCE ENGINE
        # ==============================================

        confidence_result = (

            confidence_engine.calculate(

                trust_result,

                semantic_result
            )
        )

        # ==============================================
        # POLICY ENGINE
        # ==============================================

        policy_result = (

            policy_engine.evaluate(

                confidence_result,

                trust_result
            )
        )

        # ==============================================
        # INTENT CLASSIFICATION
        # ==============================================

        intent_result = (

            intent_classifier.classify(
                patch
            )
        )

        # ==============================================
        # PATCH SIMULATION
        # ==============================================

        simulation_result = (

            patch_simulator.simulate(
                patch
            )
        )

        # ==============================================
        # GOVERNANCE AGGREGATION
        # ==============================================

        governance_result = (

            governance_aggregator.aggregate(

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

        # ==============================================
        # STORE FINAL RESULT
        # ==============================================

        validation_results.append({

            "patch":
                patch,

            "syntax_validation":
                result,

            "semantic_validation":
                semantic_result,

            "trust_analysis":
                trust_result,

            "confidence":
                confidence_result,

            "policy":
                policy_result,

            "intent":
                intent_result,

            "simulation":
                simulation_result,

            "governance":
                governance_result
        })

    # ======================================================
    # GOVERNANCE REPORT
    # ======================================================

    report_builder = (
        GovernanceReportBuilder()
    )

    governance_report = (

        report_builder.build(
            validation_results
        )
    )

    print("\n")
    print("=" * 80)
    print("🔥 GOVERNANCE REPORT")
    print("=" * 80)

    print(governance_report)

    return {

        "reviews":
            results,

        "fixes":
            fixes,

        "governance":
            validation_results
    }

