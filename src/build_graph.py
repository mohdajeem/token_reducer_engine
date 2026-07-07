import os
from utils.logger import (
    set_debug
)

from tree_sitter import Query, QueryCursor

# from semantic.graph_builder import (
#     GraphBuilder
# )
from semantic_core.graph_builder import (GraphBuilder)

from language_config import (
    LANG_CONFIG,
    LanguageManager,
    IGNORE_DIRS
)

# from semantic.capture_event import CaptureEvent
from semantic_core.capture_event import CaptureEvent

# from config.debug_flags import *
from config.settings import *

# from semantic.semantic_graph import SemanticGraph
from semantic_core.semantic_graph import SemanticGraph

# from semantic.capture_processor import CaptureProcessor
from semantic_core.capture_processor import CaptureProcessor

from config.settings import (
    AI_PROVIDER
)

from utils.logger import (
    set_debug
)

# from semantic.security.taint_traversal_engine import (
#     TaintTraversalEngine
# )
from impact_engine.taint_traversal_engine import (TaintTraversalEngine)

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


if DEBUG_GRAPH_BUILD:

    set_debug()



GLOBAL_BUILDER = None

# ==========================================================
# INIT
# ==========================================================

langmanager = LanguageManager()


# ==========================================================
# HELPER
# ==========================================================

def parse_content(content, ext):

    parser = langmanager.get_parser(ext)

    return parser.parse(
        content.encode("utf-8")
    )


# ==========================================================
# GET FUNCTION CONTEXT
# ==========================================================

def get_context(line_number, tree, ext):

    node_on_line = tree.root_node.descendant_for_point_range(
        (line_number, 0),
        (line_number, 100)
    )

    current = node_on_line

    valid_function_types = (
        langmanager.get_functional_node(ext)
    )

    while current is not None:

        if current.type in valid_function_types:

            name_node = current.child_by_field_name(
                "name"
            )

            if name_node:
                return name_node.text.decode("utf-8")

        current = current.parent

    return "GLOBAL_SCOPE"


# ==========================================================
# BUILD GRAPH
# ==========================================================

def print_tree(node, indent=0):

    print(
        "  " * indent +
        f"{node.type}"
    )

    for child in node.children:
        print_tree(child, indent + 1)


def build_graph(directory):
    global GLOBAL_BUILDER
    # first check SemanticGraph
    semantic_graph = SemanticGraph()
    processor = CaptureProcessor(semantic_graph)
    from semantic_core.semantic_registry import (SemanticRegistry)

    registry = SemanticRegistry()


    for root, dirs, files in os.walk(directory):

        # Ignore node_modules etc
        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS
        ]

        for file in files:

            abs_path = os.path.join(
                root,
                file
            )

            rel_path = os.path.relpath(
                abs_path,
                directory
            ).replace("\\", "/")

            _, ext = os.path.splitext(file)

            if not langmanager.is_supported(ext):
                continue

            if DEBUG_GRAPH_BUILD:
                print(f"📄 Parsing: {rel_path}")

            try:

                with open(
                    abs_path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    content = f.read()

            except Exception as e:
                print(
                    f"❌ Failed reading {rel_path}: {e}"
                )
                continue

            # ==================================================
            # PARSE TREE
            # ==================================================

            tree = parse_content(
                content,
                ext
            )

            # ==================================================
            # LOAD MASTER QUERY
            # ==================================================

            query_string = (
                langmanager.get_master_query(ext)
            )

            query = Query(
                LANG_CONFIG[ext]["LANGUAGE"],
                query_string
            )

            cursor = QueryCursor(query)

            matches = cursor.matches(tree.root_node)
            from semantic_core.match_extractor_fixed import safe_extract_semantic_matches

            semantic_matches = (
                safe_extract_semantic_matches(
                    matches,
                    rel_path,
                    tree
                )
            )

            # print("Semantic Match inside build function:", semantic_matches)

            registry.add_matches(
                semantic_matches
            )

    # builder = GraphBuilder()
    builder = GraphBuilder()

    GLOBAL_BUILDER = builder

    print("="*40)
    print(registry)
    print("="*40)

    graph = builder.build(
        registry.all_matches
    )

    return graph


# ==========================================================
# FINAL MAIN
# ==========================================================

if __name__ == "__main__":

    # TARGET_DIR = (
    #     r"C:\Users\ajeem\Downloads\Application"
    #     r"\CodeReviewAgent\project_with_semantic"
    #     r"\trying3\test_microservice"
    # )
    # TARGET_DIR = Path(__file__).parent.parent.parent / "test_microservice"
    TARGET_DIR = r"C:\Users\ajeem\Downloads\downloads\CoderReviewAgent2\token_reducer_system\test_microservice"
    # TARGET_DIR = r"C:\Users\ajeem\Downloads\Application\CodeReviewAgent\test_microservice"
    print("target_dir", TARGET_DIR)

    # ======================================================
    # BUILD GRAPH
    # ======================================================

    from incremental_runtime.incremental_graph_manager import (
        IncrementalGraphManager
    )
    # import semantic.match_extractor as match_extractor


    # ======================================================
    # INCREMENTAL GRAPH MANAGER
    # ======================================================

    # ======================================================
    # INITIAL FULL BUILD
    # ======================================================
    import json
    graph = build_graph(TARGET_DIR)

    print("graph: ", graph)
    print("*"*30)
    for key in graph:
        print(key," : ", graph.get(key))
    print("*"*30)

    
    print(
        "🔥 TAINT TRAVERSAL ENGINE"
    )

    print(
        "=" * 80
    )

    taint_engine = (
        TaintTraversalEngine(graph)
    )

    findings = (
        taint_engine.analyze()
    )

    print(findings)

    # # ======================================================
    # # MATCH EXTRACTOR
    # # ======================================================

    # incremental_manager = (
    #     IncrementalGraphManager(

    #         graph_builder=
    #             GLOBAL_BUILDER,

    #         match_extractor=
    #             match_extractor,
                
    #         project_root=TARGET_DIR
    #     )
    # )

    # # ======================================================
    # # RUN INCREMENTAL UPDATE
    # # ======================================================

    # graph = (

    #     incremental_manager
    #     .run_incremental_update(

    #         changed_files=[
    #             "services/userService.js"
    #         ]
    #     )
    # )

    # print("\nEXECUTION EDGES AFTER UPDATE:")
    # print(graph.get("execution_edges", [])) 

    # # ======================================================
    # # RUN REVIEW PIPELINE
    # # ======================================================

    # from pipelines.review_pipeline import (
    #     run_review_pipeline
    # )

    # print("\nEXECUTION EDGES BEFORE REVIEW:")
    # print(graph.get("execution_edges", []))

    # run_review_pipeline(

    #     graph=graph,

    #     project_root=TARGET_DIR,

    #     function_index=
    #         GLOBAL_BUILDER.function_index,

    #     provider=AI_PROVIDER
    # )

    # ======================================================
    # FUNCTION QUERY TEST
    # ======================================================

    # from semantic.query.function_query import (
    #     FunctionQuery
    # )

    # print("\n")
    # print("=" * 80)
    # print("🔥 FUNCTION QUERY")
    # print("=" * 80)

    # query = FunctionQuery(
    #     graph
    # )

    # print("\nFUNCTION CALLS:")
    # # either change here or change it to the functions 
    # fun_abs_path = os.path.join(TARGET_DIR, r"controllers/userController.js")
    # print(
    #     query.get_function_calls(
    #         fun_abs_path,
    #         "getAllUsers"
    #     )
    # )

    # print("\nROUTES:")
    # print(
    #     query.get_function_routes(
    #         fun_abs_path,
    #         "getAllUsers"
    #     )
    # )

    # print("\nTAINTED VARIABLES:")
    # print(
    #     query.get_tainted_variables(
    #         fun_abs_path,

    #         "getAllUsers"
    #     )
    # )

    # print("\nSANITIZED VARIABLES:")
    # print(

    #     query.get_sanitized_variables(

    #         fun_abs_path,

    #         "getAllUsers"
    #     )
    # )

    # print("\nDOWNSTREAM:")
    # print(
    #     query.get_downstream_calls(

    #         fun_abs_path,

    #         "getAllUsers"
    #     )
    # )

    # # ======================================================
    # # PATCH SEMANTIC EXTRACTION TEST
    # # ======================================================

    # from semantic.patch_semantic_extractor import (
    #     PatchSemanticExtractor
    # )

    # print("\n")
    # print("=" * 80)
    # print("🔥 PATCH SEMANTIC EXTRACTION")
    # print("=" * 80)

    # extractor = PatchSemanticExtractor()

    # sample_patch = """
    # + const hashedPassword = hashAndSalt(req.body.password);
    # + userService.fetchUsers(req.body.email, hashedPassword)
    # + // secure password handling
    # """

    # result = extractor.extract(
    #     sample_patch
    # )

    # print(result)

    # ======================================================
    # GOVERNANCE TEST SUITE
    # ======================================================

    # from tests.governance.test_governance_pipeline import (
    #     run_governance_test
    # )

    # run_governance_test(
    #     graph
    # )

    # from tests.incremental.test_graph_invalidator import (
    #     run_graph_invalidator_test
    # )

    # # ==========================================================
    # # GRAPH INVALIDATOR TEST
    # # ==========================================================

    # run_graph_invalidator_test()





# ==========================================================
# FINAL MAIN
# ==========================================================

# if __name__ == "__main__":

#     TARGET_DIR = (
#         r"C:\Users\ajeem\Downloads\Application"
#         r"\CodeReviewAgent\project_with_semantic"
#         r"\trying3\test_microservice"
#     )

#     # ======================================================
#     # BUILD GRAPH
#     # ======================================================

#     graph = build_graph(
#         TARGET_DIR
#     )

#     # import json
#     # print("Graph: \n",json.dumps(graph, indent=4))

#     # import json
#     # import os

#     # graph = build_graph(TARGET_DIR)

#     # # Get the exact path of the current working directory
#     # current_dir = os.getcwd()
#     # file_path = os.path.join(current_dir, "graph_json.json")

#     # # Write to the file
#     # with open(file_path, "w", encoding="utf-8") as file:
#     #     json.dump(graph, file, indent=4)

#     # print(f"Graph successfully saved to: {file_path}")


#     # ======================================================
#     # RUN REVIEW PIPELINE
#     # ======================================================

#     from pipelines.review_pipeline import (
#         run_review_pipeline
#     )

#     run_review_pipeline(

#         graph=graph,

#         project_root=TARGET_DIR,

#         function_index=
#             GLOBAL_BUILDER.function_index,

#         provider=AI_PROVIDER
#         # provider="groq"
#     )

#     from semantic.query.function_query import (
#         FunctionQuery
#     )

#     # ==========================================================
#     # FUNCTION QUERY TEST
#     # ==========================================================

#     print("\n")
#     print("=" * 80)
#     print("🔥 FUNCTION QUERY")
#     print("=" * 80)

#     query = FunctionQuery(
#         graph
#     )

#     print("\nFUNCTION CALLS:")
#     print(

#         query.get_function_calls(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     print("\nROUTES:")
#     print(

#         query.get_function_routes(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     print("\nTAINTED VARIABLES:")
#     print(

#         query.get_tainted_variables(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     print("\nSANITIZED VARIABLES:")
#     print(

#         query.get_sanitized_variables(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     print("\nDOWNSTREAM:")
#     print(

#         query.get_downstream_calls(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     from semantic.patch_semantic_extractor import (
#         PatchSemanticExtractor
#     )

#     # ==========================================================
#     # PATCH SEMANTIC EXTRACTION TEST
#     # ==========================================================

#     print("\n")
#     print("=" * 80)
#     print("🔥 PATCH SEMANTIC EXTRACTION")
#     print("=" * 80)

#     extractor = PatchSemanticExtractor()

#     sample_patch = """
#     + const hashedPassword = hashAndSalt(req.body.password);
#     + userService.fetchUsers(req.body.email, hashedPassword)
#     + // secure password handling
#     """

#     result = extractor.extract(
#         sample_patch
#     )

#     print(result)

#     # from ai_reviewer.fixes.patch_trust_analyzer import (
#     #     PatchTrustAnalyzer
#     # )


#     # # ==========================================================
#     # # PATCH TRUST ANALYZER TEST
#     # # ==========================================================

#     # print("\n")
#     # print("=" * 80)
#     # print("🔥 PATCH TRUST ANALYZER")
#     # print("=" * 80)

#     # trust_analyzer = PatchTrustAnalyzer(
#     #     graph
#     # )

#     # sample_patch = {

#     #     "file":
#     #         "controllers/userController.js",

#     #     "function":
#     #         "getAllUsers",

#     #     "patch":
#     #         """
#     # + const hashedPassword = hashPassword(req.body.password)
#     # + return bcrypt.hash(hashedPassword)
#     #         """
#     # }

#     # trust_result = trust_analyzer.analyze(
#     #     sample_patch
#     # )

#     # print(trust_result)


#     # from ai_reviewer.fixes.confidence_engine import (
#     #     ConfidenceEngine
#     # )

#     # # ==========================================================
#     # # CONFIDENCE ENGINE TEST
#     # # ==========================================================

#     # print("\n")
#     # print("=" * 80)
#     # print("🔥 CONFIDENCE ENGINE")
#     # print("=" * 80)

#     # engine = ConfidenceEngine()

#     # # trust_result = {

#     # # "findings": [

#     # #     {
#     # #         "type":
#     # #             "UNKNOWN_FUNCTION",

#     # #         "message":
#     # #             "hashPassword not found"
#     # #     }
#     # # ]
#     # # }

#     # semantic_validation = {

#     # "valid": True
#     # }

#     # confidence = engine.calculate(

#     # trust_result,

#     # semantic_validation
#     # )

#     # print(confidence)


#     # from ai_reviewer.fixes.policy_engine import (
#     #     PolicyEngine
#     # )# ==========================================================
#     # # POLICY ENGINE TEST
#     # # ==========================================================

#     # print("\n")
#     # print("=" * 80)
#     # print("🔥 POLICY ENGINE")
#     # print("=" * 80)

#     # policy_engine = PolicyEngine()

#     # policy_result = policy_engine.evaluate(

#     #     confidence,

#     #     trust_result
#     # )

#     # print(policy_result)

#     # from ai_reviewer.fixes.patch_intent_classifier import (
#     #     PatchIntentClassifier
#     # )

#     # # ==========================================================
#     # # PATCH INTENT CLASSIFIER TEST
#     # # ==========================================================

#     # print("\n")
#     # print("=" * 80)
#     # print("🔥 PATCH INTENT CLASSIFIER")
#     # print("=" * 80)

#     # classifier = PatchIntentClassifier()

#     # sample_patch = {

#     #     "patch":
#     #         "// review manually"
#     # }

#     # intent_result = classifier.classify(
#     #     sample_patch
#     # )

#     # print(intent_result)


#     # from ai_reviewer.fixes.patch_simulator import (
#     #     PatchSimulator
#     # )

#     # # ==========================================================
#     # # PATCH SIMULATOR TEST
#     # # ==========================================================

#     # print("\n")
#     # print("=" * 80)
#     # print("🔥 PATCH SIMULATOR")
#     # print("=" * 80)

#     # simulator = PatchSimulator(
#     #     graph
#     # )

#     # sample_patch = {

#     #     "file":
#     #         "services/userService.js",

#     #     "function":
#     #         "fetchUsers",

#     #     "patch":
#     #         """
#     # + const hashedPassword = hashPassword(password)
#     # + return bcrypt.hash(hashedPassword)
#     #         """
#     # }

#     # simulation_result = simulator.simulate(
#     #     sample_patch
#     # )

#     # print(simulation_result)


#     # from ai_reviewer.fixes.governance_aggregator import (
#     #     GovernanceAggregator
#     # )

#     # # ==========================================================
#     # # GOVERNANCE AGGREGATOR TEST
#     # # ==========================================================

#     # print("\n")
#     # print("=" * 80)
#     # print("🔥 GOVERNANCE AGGREGATOR")
#     # print("=" * 80)
#     # print("Trust result:",trust_result)

#     # aggregator = GovernanceAggregator()


#     # governance_result = aggregator.aggregate(

#     #     semantic_validation={

#     #         "valid": True
#     #     },

#     #     trust_analysis=trust_result,

#     #     confidence_result=confidence,

#     #     intent_result=intent_result,

#     #     simulation_result=simulation_result,

#     #     policy_result=policy_result
#     # )

#     # print(governance_result)



# ==========================================================
# TEST
# ==========================================================

# if __name__ == "__main__":

#     # TARGET_DIR = r"C:\Users\ajeem\Downloads\Application\CodeReviewAgent\test_microservice\routes"
#     # TARGET_DIR = r"C:\Users\ajeem\Downloads\Application\CodeReviewAgent\test_microservice"
#     TARGET_DIR = r"C:\Users\ajeem\Downloads\Application\CodeReviewAgent\project_with_semantic\trying2\test_microservice"

#     graph = build_graph(TARGET_DIR)

#     # make a snapshot
#     from semantic.snapshot_manager import (
#         SnapshotManager
#     )

#     snapshot = SnapshotManager()


#     import json
#     from semantic.graph_diff import (
#         GraphDiff
#     )

#     # ==========================================================
#     # LOAD OLD SNAPSHOT
#     # ==========================================================

#     old_graph = snapshot.load_snapshot()

#     # ==========================================================
#     # GENERATE DIFF
#     # ==========================================================

#     diff_engine = GraphDiff(

#         old_graph=old_graph,

#         new_graph=graph
#     )

#     diff = diff_engine.generate_diff()

#     print("\n")
#     print("=" * 80)
#     print("🔥 SEMANTIC DIFF")
#     print("=" * 80)

#     print(json.dumps(
#         diff,
#         indent=2
#     ))

#     # ==========================================================
#     # SAVE NEW SNAPSHOT
#     # ==========================================================
#     snapshot.save_snapshot(
#         graph
#     )

#     print("\n✅ Snapshot saved.")

#     # snapshot.save_snapshot(graph)

    
#     import json

#     print("\n")
#     print("=" * 80)
#     print("🔥 SEMANTIC GRAPH")
#     print("=" * 80)

#     print(
#         json.dumps(
#             graph,
#             indent=2
#         )
#     )

#     from semantic.impact_analysis import (
#         ImpactAnalysis
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 IMPACT ANALYSIS")
#     print("=" * 80)

#     analysis = ImpactAnalysis(graph)

#     # ==========================================================
#     # IMPACTED ROUTES BY DB MODEL
#     # ==========================================================

#     routes = (
#         analysis.find_impacted_routes_by_db(
#             "User"
#         )
#     )

#     print("\n🚦 ROUTES IMPACTED BY User MODEL:\n")

#     print(json.dumps(
#         routes,
#         indent=2
#     ))

#     # ==========================================================
#     # DOWNSTREAM EXECUTION
#     # ==========================================================

#     downstream = (
#         analysis.find_downstream_calls(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     print("\n📉 DOWNSTREAM EXECUTION:\n")

#     print(json.dumps(
#         downstream,
#         indent=2
#     ))

#     from semantic.change_detector import (
#         ChangeDetector
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 CHANGE DETECTOR")
#     print("=" * 80)

#     detector = ChangeDetector()

#     diff_text = detector.get_git_diff()

#     changes = detector.extract_changes(
#         diff_text
#     )

#     print(json.dumps(
#         changes,
#         indent=2
#     ))
#     from semantic.change_classifier import (
#         ChangeClassifier
#     )

#     classifier = ChangeClassifier(
#         diff
#     )

#     classified_changes = (
#         classifier.classify()
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 CHANGE CLASSIFICATION")
#     print("=" * 80)

#     print(json.dumps(
#         classified_changes,
#         indent=2
#     ))

#     from semantic.review_generator import (
#         ReviewGenerator
#     )

#     review_generator = ReviewGenerator(

#         classified_changes,

#         graph
#     )

#     reviews = (
#         review_generator.generate_reviews()
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 AI REVIEW")
#     print("=" * 80)

#     print(json.dumps(
#         reviews,
#         indent=2
#     ))
#     from ai.review_workflow import (
#         build_review_graph
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 LANGGRAPH AI REVIEW")
#     print("=" * 80)

#     workflow = build_review_graph()

#     result = workflow.invoke({

#         "graph": graph,

#         "semantic_diff": diff,

#         "classified_changes": [],

#         "impact_analysis": {},

#         "reviews": []
#     })

#     print(json.dumps(
#         result,
#         indent=2
#     ))


# NEW FEATURE TESTING 

# if __name__ == "__main__":

#     import json

#     TARGET_DIR = (
#         r"C:\Users\ajeem\Downloads\Application"
#         r"\CodeReviewAgent\project_with_semantic"
#         r"\trying3\test_microservice"
#     )

#     # ======================================================
#     # BUILD GRAPH
#     # ======================================================

#     graph = build_graph(
#         TARGET_DIR
#     )

#     # ======================================================
#     # PRINT GRAPH
#     # ======================================================

#     print("\n")
#     print("=" * 80)
#     print("🔥 SEMANTIC GRAPH")
#     print("=" * 80)

#     print(json.dumps(

#         graph,

#         indent=2
#     ))

#     # ======================================================
#     # PRINT SYMBOL TABLE
#     # ======================================================

#     print("\n")
#     print("=" * 80)
#     print("🔥 SYMBOL TABLE")
#     print("=" * 80)

#     # builder = GraphBuilder()


#     # print(json.dumps(

#     #     builder.symbol_table.aliases,

#     #     indent=2
#     # ))

#     # print(json.dumps(
#     #     GLOBAL_BUILDER.symbol_table.aliases,
#     #     indent=2
#     # ))
#     print(json.dumps({
#         "aliases":
#             GLOBAL_BUILDER.symbol_table.aliases,

#         "destructured":
#             GLOBAL_BUILDER.symbol_table.destructured

#     }, indent=2))

#     # ==========================================================
#     # IMPACT RADIUS TEST
#     # ==========================================================

#     from ai_reviewer.impact.impact_radius import (
#         ImpactRadius
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 IMPACT RADIUS ENGINE")
#     print("=" * 80)

#     impact_engine = ImpactRadius(
#         graph
#     )

#     impact = (
#         impact_engine.find_affected_by_function(

#             "controllers/userController.js",

#             "getAllUsers"
#         )
#     )

#     print(
#         json.dumps(
#             impact,
#             indent=2
#         )
#     )

#     # ==========================================================
#     # CONTEXT EXTRACTOR TEST
#     # ==========================================================

#     from ai_reviewer.context.context_extractor import (
#         ContextExtractor
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 CONTEXT EXTRACTOR")
#     print("=" * 80)

#     extractor = ContextExtractor(

#         graph=graph,

#         project_root=TARGET_DIR
#     )

#     context = extractor.extract_context(
#         impact
#     )

#     print(
#         json.dumps(
#             context,
#             indent=2
#         )
#     )

#     # ==========================================================
#     # REVIEW PROMPT TEST
#     # ==========================================================

#     from ai_reviewer.prompts.review_prompt_builder import (
#         ReviewPromptBuilder
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 REVIEW PROMPT")
#     print("=" * 80)

#     prompt_builder = ReviewPromptBuilder()

#     prompt = prompt_builder.build_prompt(

#         impact_result=impact,

#         context_result=context
#     )

#     print(prompt)

#     # ==========================================================
#     # AI REVIEW TEST
#     # ==========================================================

#     from ai_reviewer.reviewers.reviewer_factory import (
#         ReviewerFactory
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 AI REVIEW")
#     print("=" * 80)

#     reviewer = ReviewerFactory.create(
#         "groq"
#     )

#     review = reviewer.generate_review(
#         prompt
#     )

#     # ==========================================================
#     # PARSE REVIEW
#     # ==========================================================

#     from ai_reviewer.reviewers.review_parser import (
#         ReviewParser
#     )

#     parser = ReviewParser()

#     parsed_review = parser.parse(
#         review
#     )

#     print(

#         json.dumps(

#             parsed_review,

#             indent=2
#         )
#     )

#     # ==========================================================
#     # CHANGE ANALYZER TEST
#     # ==========================================================

#     from ai_reviewer.impact.change_analyzer import (
#         ChangeAnalyzer
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 CHANGE ANALYZER")
#     print("=" * 80)

#     change_analyzer = ChangeAnalyzer(
#         graph=graph,
#         repo_path=TARGET_DIR,
#         function_index=GLOBAL_BUILDER.function_index
#     )

#     diff_text = (
#         change_analyzer.get_git_diff()
#     )

#     changes = (
#         change_analyzer.analyze_changes(
#             diff_text
#         )
#     )

#     print(

#         json.dumps(

#             changes,

#             indent=2
#         )
#     )

#     # ==========================================================
#     # AUTONOMOUS REVIEW ORCHESTRATOR
#     # ==========================================================

#     from ai_reviewer.orchestrator.review_orchestrator import (
#         ReviewOrchestrator
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 AUTONOMOUS REVIEW PIPELINE")
#     print("=" * 80)

#     orchestrator = ReviewOrchestrator(

#         graph=graph,

#         project_root=TARGET_DIR,

#         function_index=GLOBAL_BUILDER.function_index,

#         provider="groq"
#     )

#     results = orchestrator.run()

#     print("\n")
#     print("=" * 80)
#     print("🔥 FINAL REVIEW RESULTS")
#     print("=" * 80)

#     print(
#         json.dumps(
#             results,
#             indent=2
#         )
#     )

#     # ==========================================================
#     # FIX GENERATION TEST
#     # ==========================================================

#     from ai_reviewer.fixes.fix_generator import (
#         FixGenerator
#     )

#     print("\n")
#     print("=" * 80)
#     print("🔥 FIX GENERATION")
#     print("=" * 80)

#     reviewer = ReviewerFactory.create(
#         "groq"
#     )

#     fix_generator = FixGenerator(
#         reviewer
#     )

#     latest_review = (
#         results[0]["reviews"]
#     )

#     # latest_context = context

#     latest_context = (
#         results[0]["context"]
#     )

#     fixes = (
#         fix_generator.generate_fixes(

#             review_results=latest_review,

#             context_result=latest_context,

#             changes=changes
#         )
#     )

#     print(

#         json.dumps(

#             fixes,

#             indent=2
#         )
#     )


