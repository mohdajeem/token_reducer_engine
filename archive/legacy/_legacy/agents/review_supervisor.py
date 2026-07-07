from agents.security_agent import (
    SecurityAgent
)

from agents.performance_agent import (
    PerformanceAgent
)

from agents.api_agent import (
    APIAgent
)


class ReviewSupervisor:

    def __init__(

        self,

        provider="groq"
    ):

        self.security_agent = (
            SecurityAgent(provider)
        )

        self.performance_agent = (
            PerformanceAgent(provider)
        )

        self.api_agent = (
            APIAgent(provider)
        )

    # ======================================================
    # RUN ALL AGENTS
    # ======================================================

    def review(

        self,

        classified_changes,

        impact_analysis
    ):

        security_review = (
            self.security_agent.review(

                classified_changes,

                impact_analysis
            )
        )

        performance_review = (
            self.performance_agent.review(

                classified_changes,

                impact_analysis
            )
        )

        api_review = (
            self.api_agent.review(

                classified_changes,

                impact_analysis
            )
        )

        return {

            "security":
            security_review,

            "performance":
            performance_review,

            "api":
            api_review
        }