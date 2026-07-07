class ReviewGenerator:

    def __init__(

        self,

        classified_changes,

        graph
    ):

        self.changes = (
            classified_changes
        )

        self.graph = graph

    # ======================================================
    # GENERATE REVIEWS
    # ======================================================

    def generate_reviews(self):

        reviews = []

        for change in self.changes:

            review = self.generate_review(
                change
            )

            reviews.append(review)

        return reviews

    # ======================================================
    # SINGLE REVIEW
    # ======================================================

    def generate_review(

        self,

        change
    ):

        change_type = change.get(
            "type"
        )

        severity = change.get(
            "severity"
        )

        # ==================================================
        # BREAKING API
        # ==================================================

        if (
            change_type
            ==
            "BREAKING_API_CHANGE"
        ):

            return {

                "severity":
                severity,

                "title":
                "Breaking API Change",

                "summary":
                (
                    f"Route removed: "
                    f"{change.get('method').upper()} "
                    f"{change.get('route')}"
                ),

                "risk":
                [

                    "Frontend integrations may fail",

                    "Mobile apps may break",

                    "Downstream consumers affected"
                ],

                "recommendation":
                (
                    "Consider API versioning "
                    "or deprecation strategy."
                )
            }

        # ==================================================
        # NEW PUBLIC API
        # ==================================================

        elif (
            change_type
            ==
            "NEW_PUBLIC_API"
        ):

            return {

                "severity":
                severity,

                "title":
                "New Public API",

                "summary":
                (
                    f"New route added: "
                    f"{change.get('method').upper()} "
                    f"{change.get('route')}"
                ),

                "risk":
                [

                    "Authentication validation required",

                    "Rate limiting may be needed",

                    "Public surface area increased"
                ],

                "recommendation":
                (
                    "Verify auth, validation, "
                    "and monitoring coverage."
                )
            }

        # ==================================================
        # DATABASE CHANGE
        # ==================================================

        elif (
            change_type
            ==
            "DATABASE_CHANGE"
        ):

            return {

                "severity":
                severity,

                "title":
                "Database Access Change",

                "summary":
                (
                    f"New DB operation: "
                    f"{change.get('operation')}"
                ),

                "risk":
                [

                    "Potential query performance impact",

                    "Schema compatibility risk",

                    "Database load may increase"
                ],

                "recommendation":
                (
                    "Review indexes and query plans."
                )
            }

        # ==================================================
        # EXECUTION PATH CHANGE
        # ==================================================

        elif (
            change_type
            ==
            "NEW_EXECUTION_PATH"
        ):

            return {

                "severity":
                severity,

                "title":
                "Execution Flow Changed",

                "summary":
                (
                    "New execution dependency "
                    "detected."
                ),

                "risk":
                [

                    "Unexpected side effects",

                    "Circular dependency risk",

                    "Additional runtime coupling"
                ],

                "recommendation":
                (
                    "Review downstream "
                    "execution impacts."
                )
            }

        # ==================================================
        # DEFAULT
        # ==================================================

        return {

            "severity":
            severity,

            "title":
            "Semantic Change",

            "summary":
            change.get("reason"),

            "risk": [],

            "recommendation":
            "Review manually."
        }