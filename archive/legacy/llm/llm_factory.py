from llm.openai_provider import (
    OpenAIProvider
)

from llm.gemini_provider import (
    GeminiProvider
)

from llm.groq_provider import (
    GroqProvider
)


class LLMFactory:

    @staticmethod
    def create(

        provider_name
    ):

        provider_name = (
            provider_name.lower()
        )

        if provider_name == "openai":

            return OpenAIProvider()

        elif provider_name == "gemini":

            return GeminiProvider()

        elif provider_name == "groq":

            return GroqProvider()

        else:

            raise Exception(

                f"Unsupported provider: "
                f"{provider_name}"
            )