# ==========================================================
# GEMINI REVIEWER
# ==========================================================

import os

import google.generativeai as genai

from dotenv import load_dotenv

from ai_reviewer.reviewers.base_reviewer import (
    BaseReviewer
)

# ==========================================================
# LOAD ENV
# ==========================================================

load_dotenv()

# ==========================================================
# CONFIGURE GEMINI
# ==========================================================

genai.configure(

    api_key=os.getenv(
        "GEMINI_API_KEY"
    )
)


class GeminiReviewer(BaseReviewer):

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        self.model = genai.GenerativeModel(

            "gemini-1.5-flash"
        )

    # ======================================================
    # GENERATE REVIEW
    # ======================================================

    def generate_review(

        self,

        prompt
    ):

        response = self.model.generate_content(
            prompt
        )

        return response.text