from llm.llm_factory import (
    LLMFactory
)


class APIAgent:

    def __init__(

        self,

        provider="groq"
    ):

        self.llm = (
            LLMFactory.create(
                provider
            )
        )

    def review(

        self,

        classified_changes,

        impact_analysis
    ):

        prompt = f"""

You are an API Architect.

Analyze these semantic changes:

{classified_changes}

Impact analysis:

{impact_analysis}

Focus ONLY on:

1. Breaking API changes
2. Contract compatibility
3. Route stability
4. Client impact
5. Versioning concerns
6. Public API exposure

Return concise findings.

"""

        return self.llm.invoke(
            prompt
        )