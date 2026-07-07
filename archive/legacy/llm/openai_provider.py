import os

from langchain_openai import (
    ChatOpenAI
)

from llm.base_provider import (
    BaseLLMProvider
)


class OpenAIProvider(

    BaseLLMProvider
):

    def __init__(self):

        self.llm = ChatOpenAI(

            model="gpt-4o-mini",

            api_key=os.getenv(
                "OPENAI_API_KEY"
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