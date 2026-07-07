# ==========================================================
# REVIEW ORCHESTRATOR
# ==========================================================

import json

from ai_reviewer.impact.change_analyzer import (
    ChangeAnalyzer
)

from ai_reviewer.impact.impact_radius import (
    ImpactRadius
)

from ai_reviewer.context.context_extractor import (
    ContextExtractor
)

from ai_reviewer.prompts.review_prompt_builder import (
    ReviewPromptBuilder
)

from ai_reviewer.reviewers.reviewer_factory import (
    ReviewerFactory
)

from ai_reviewer.reviewers.review_parser import (
    ReviewParser
)


class ReviewOrchestrator:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        graph,

        project_root,

        function_index,

        provider="groq"
    ):

        self.graph = graph

        self.project_root = project_root

        self.function_index = function_index

        self.provider = provider

        self.latest_changes = None

    # ======================================================
    # RUN REVIEW PIPELINE
    # ======================================================

    def run(self):

        # ==================================================
        # CHANGE ANALYSIS
        # ==================================================

        change_analyzer = ChangeAnalyzer(

            graph=self.graph,

            repo_path=self.project_root,

            function_index=self.function_index
        )

        diff_text = (
            change_analyzer.get_git_diff()
        )

        changes = (
            change_analyzer.analyze_changes(
                diff_text
            )
        )

        self.latest_changes = changes

        print("\n")
        print("=" * 80)
        print("🔥 DETECTED CHANGES")
        print("=" * 80)

        print(
            json.dumps(
                changes,
                indent=2
            )
        )

        # ==================================================
        # NO CHANGES
        # ==================================================

        if not changes["changed_functions"]:

            print("\nNo semantic changes detected.")

            return []

        # ==================================================
        # IMPACT ENGINE
        # ==================================================

        impact_engine = ImpactRadius(
            self.graph
        )

        all_reviews = []

        # ==================================================
        # REVIEW EACH CHANGED FUNCTION
        # ==================================================

        for changed in changes[

            "changed_functions"
        ]:

            file_path = changed.get(
                "file"
            )

            function_name = changed.get(
                "function"
            )

            print("\n")
            print("=" * 80)
            print(
                f"🔥 REVIEWING: "
                f"{function_name}"
            )
            print("=" * 80)

            # ==============================================
            # IMPACT ANALYSIS
            # ==============================================

            impact = (
                impact_engine
                .find_affected_by_function(

                    file_path,

                    function_name
                )
            )

            print("\nIMPACT:")

            print(
                json.dumps(
                    impact,
                    indent=2
                )
            )

            # ==============================================
            # CONTEXT EXTRACTION
            # ==============================================

            extractor = ContextExtractor(

                graph=self.graph,

                project_root=self.project_root
            )

            context = (
                extractor.extract_context(
                    impact
                )
            )

            # ==============================================
            # PROMPT BUILDING
            # ==============================================

            prompt_builder = (
                ReviewPromptBuilder()
            )

            # prompt = (
            #     prompt_builder.build_prompt(

            #         impact_result=impact,

            #         context_result=context
            #     )
            # )

            prompt = (
                prompt_builder.build_prompt(

                    impact_result=impact,

                    context_result=context,

                    changes=changes
                )
            )

            # ==============================================
            # AI REVIEW
            # ==============================================

            reviewer = (
                ReviewerFactory.create(
                    self.provider
                )
            )

            raw_review = (
                reviewer.generate_review(
                    prompt
                )
            )

            # ==============================================
            # PARSE REVIEW
            # ==============================================

            parser = ReviewParser()

            parsed_review = (
                parser.parse(
                    raw_review
                )
            )

            # ==============================================
            # STORE
            # ==============================================

            all_reviews.append({

                "changed_function": changed,

                "impact": impact,

                "context": context,

                "reviews": parsed_review
            })

        return all_reviews