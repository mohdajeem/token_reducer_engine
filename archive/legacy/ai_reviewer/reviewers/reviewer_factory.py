# ==========================================================
# REVIEWER FACTORY
# ==========================================================

from ai_reviewer.reviewers.groq_reviewer import (
    GroqReviewer
)

from ai_reviewer.reviewers.gemini_reviewer import (
    GeminiReviewer
)


class ReviewerFactory:

    # ======================================================
    # CREATE REVIEWER
    # ======================================================

    @staticmethod
    def create(

        provider
    ):

        provider = provider.lower()

        # ==================================================
        # GROQ
        # ==================================================

        if provider == "groq":

            return GroqReviewer()

        # ==================================================
        # GEMINI
        # ==================================================

        elif provider == "gemini":

            return GeminiReviewer()

        # ==================================================
        # UNKNOWN
        # ==================================================

        raise ValueError(

            f"Unsupported provider: {provider}"
        )