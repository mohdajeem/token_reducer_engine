from llm.llm_factory import (
    LLMFactory
)


class LLMReviewNode:

    def __init__(

        self,

        provider="groq"
    ):

        self.llm = (
            LLMFactory.create(
                provider
            )
        )

    # ======================================================
    # REVIEW
    # ======================================================

    def review(

        self,

        classified_changes,

        impact_analysis
    ):

        prompt = f"""

You are a Staff Engineer performing
semantic code review.

Analyze these classified changes:

{classified_changes}

Impact analysis:

{impact_analysis}

Generate:

1. Risks
2. Breaking changes
3. Security concerns
4. Performance concerns
5. Recommended actions

"""

        return self.llm.invoke(
            prompt
        )