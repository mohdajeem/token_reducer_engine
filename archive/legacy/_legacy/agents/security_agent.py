from llm.llm_factory import (
    LLMFactory
)


class SecurityAgent:

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

You are a Senior Security Engineer.

Analyze the following semantic changes:

{classified_changes}

Impact analysis:

{impact_analysis}

Focus ONLY on:

1. Authentication risks
2. Authorization flaws
3. Data exposure risks
4. Injection vulnerabilities
5. Missing validation
6. Public API exposure
7. Sensitive data handling

Return concise engineering findings.

"""

        return self.llm.invoke(
            prompt
        )