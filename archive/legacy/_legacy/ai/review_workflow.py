from typing import TypedDict

from langgraph.graph import (
    StateGraph,
    END
)

from semantic.impact_analysis import (
    ImpactAnalysis
)

from semantic.change_classifier import (
    ChangeClassifier
)

from agents.review_supervisor import (
    ReviewSupervisor
)


# ==========================================================
# GRAPH STATE
# ==========================================================

class ReviewState(TypedDict):

    graph: dict

    semantic_diff: dict

    classified_changes: list

    impact_analysis: dict

    reviews: list


# ==========================================================
# STEP 1
# IMPACT ANALYSIS
# ==========================================================

def analyze_impact(

    state: ReviewState
):

    graph = state["graph"]

    analysis = ImpactAnalysis(
        graph
    )

    impacted_routes = (
        analysis.find_impacted_routes_by_db(
            "User"
        )
    )

    state["impact_analysis"] = {

        "impacted_routes":
        impacted_routes
    }

    return state


# ==========================================================
# STEP 2
# CLASSIFY CHANGES
# ==========================================================

def classify_changes(

    state: ReviewState
):

    classifier = ChangeClassifier(

        state["semantic_diff"]
    )

    classified = (
        classifier.classify()
    )

    state["classified_changes"] = (
        classified
    )

    return state


# ==========================================================
# STEP 3
# GENERATE REVIEWS
# ==========================================================

def generate_reviews(

    state: ReviewState
):

    classified_changes = (
        state["classified_changes"]
    )

    # ======================================================
    # NO CHANGES
    # ======================================================

    if not classified_changes:

        state["reviews"] = [

            "No semantic changes detected."
        ]

        return state

    # ======================================================
    # LLM REVIEW
    # ======================================================

    reviewer = ReviewSupervisor(

        provider="groq"
    )
    # reviewer = LLMReviewNode(

    #     provider="groq"
    # )

    llm_review = reviewer.review(

        classified_changes=(
            classified_changes
        ),

        impact_analysis=(
            state["impact_analysis"]
        )
    )

    state["reviews"] = [

        llm_review
    ]

    return state

# ==========================================================
# BUILD GRAPH
# ==========================================================

def build_review_graph():

    workflow = StateGraph(
        ReviewState
    )

    workflow.add_node(
        "impact_analysis",
        analyze_impact
    )

    workflow.add_node(
        "classify_changes",
        classify_changes
    )

    workflow.add_node(
        "generate_reviews",
        generate_reviews
    )

    # ======================================================
    # FLOW
    # ======================================================

    workflow.set_entry_point(
        "impact_analysis"
    )

    workflow.add_edge(

        "impact_analysis",

        "classify_changes"
    )

    workflow.add_edge(

        "classify_changes",

        "generate_reviews"
    )

    workflow.add_edge(

        "generate_reviews",

        END
    )

    return workflow.compile()