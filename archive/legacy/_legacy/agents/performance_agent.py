from llm.llm_factory import (
    LLMFactory
)


class PerformanceAgent:

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

You are a Staff Performance Engineer.

Analyze these semantic changes:

{classified_changes}

Impact analysis:

{impact_analysis}

Focus ONLY on:

1. Database performance
2. Query efficiency
3. Memory usage
4. CPU load
5. N+1 query risks
6. Large payload risks
7. Scaling concerns

Return concise findings.

"""

        return self.llm.invoke(
            prompt
        )