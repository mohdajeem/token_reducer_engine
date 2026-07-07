import os

from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from llm.base_provider import (
    BaseLLMProvider
)


class GeminiProvider(

    BaseLLMProvider
):

    def __init__(self):

        self.llm = (
            ChatGoogleGenerativeAI(

                model="gemini-2.5-flash",

                google_api_key=os.getenv(
                    "GEMINI_API_KEY"
                ),

                temperature=0
            )
        )

    def invoke(

        self,

        prompt
    ):

        response = self.llm.invoke(
            prompt
        )

        return response.content