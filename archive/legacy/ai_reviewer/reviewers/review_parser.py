# ==========================================================
# REVIEW PARSER
# ==========================================================

import json
import re


class ReviewParser:

    # ======================================================
    # PARSE REVIEW
    # ======================================================

    def parse(

        self,

        raw_review
    ):

        # ==================================================
        # TRY DIRECT JSON
        # ==================================================

        try:

            parsed = json.loads(
                raw_review
            )

            return self.normalize_reviews(
                parsed
            )

        except:
            pass

        # ==================================================
        # TRY JSON BLOCK EXTRACTION
        # ==================================================

        json_match = re.search(

            r"```json(.*?)```",

            raw_review,

            re.DOTALL
        )

        if json_match:

            json_text = (
                json_match.group(1)
                .strip()
            )

            try:

                parsed = json.loads(
                    json_text
                )

                return self.normalize_reviews(
                    parsed
                )

            except:

                pass

        # ==================================================
        # FALLBACK
        # ==================================================

        return [

            {
                "severity": "INFO",

                "category": "UNSTRUCTURED_REVIEW",

                "title": "Raw AI Review",

                "description": raw_review,

                "recommendation": None,

                "affected_function": None,

                "confidence": 0.5
            }
        ]

    # ======================================================
    # NORMALIZE
    # ======================================================

    def normalize_reviews(

        self,

        parsed
    ):

        normalized = []

        # ==================================================
        # SINGLE OBJECT
        # ==================================================

        if isinstance(parsed, dict):

            parsed = [parsed]

        # ==================================================
        # VALIDATE
        # ==================================================

        for item in parsed:

            normalized.append({

                "severity":
                    item.get(
                        "severity",
                        "INFO"
                    ),

                "category":
                    item.get(
                        "category",
                        "GENERAL"
                    ),

                "title":
                    item.get(
                        "title",
                        "Untitled Review"
                    ),

                "description":
                    item.get(
                        "description",
                        ""
                    ),

                "recommendation":
                    item.get(
                        "recommendation"
                    ),

                "affected_function":
                    item.get(
                        "affected_function"
                    ),

                "confidence":
                    item.get(
                        "confidence",
                        0.5
                    )
            })

        return normalized