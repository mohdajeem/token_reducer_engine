# ==========================================================
# GROQ REVIEWER
# ==========================================================

import os

from groq import Groq

from dotenv import load_dotenv

from ai_reviewer.reviewers.base_reviewer import (
    BaseReviewer
)

# ==========================================================
# LOAD ENV
# ==========================================================

load_dotenv()


class GroqReviewer(BaseReviewer):

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        self.client = Groq(

            api_key=os.getenv(
                "GROQ_API_KEY"
            )
        )

    # ======================================================
    # GENERATE REVIEW
    # ======================================================

    def generate_review(

        self,

        prompt
    ):

        response = self.client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[

                {
                    "role": "user",

                    "content": prompt
                }
            ],

            temperature=0.2
        )

        return (

            response.choices[0]
            .message
            .content
        )