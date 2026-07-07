import os

from langchain_groq import (
    ChatGroq
)

from llm.base_provider import (
    BaseLLMProvider
)


class GroqProvider(

    BaseLLMProvider
):

    def __init__(self):

        self.llm = ChatGroq(

            model="llama-3.3-70b-versatile",

            api_key=os.getenv(
                "GROQ_API_KEY"
            ),

            temperature=0
        )

    def invoke(

        self,

        prompt
    ):

        response = self.llm.invoke(
            prompt
        )

        return response.content