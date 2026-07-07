class ChangeClassifier:

    def __init__(

        self,

        semantic_diff
    ):

        self.diff = semantic_diff

    # ======================================================
    # MAIN CLASSIFIER
    # ======================================================

    def classify(self):

        findings = []

        findings.extend(

            self.classify_new_routes()
        )

        findings.extend(

            self.classify_removed_routes()
        )

        findings.extend(

            self.classify_db_changes()
        )

        findings.extend(

            self.classify_execution_changes()
        )

        return findings

    # ======================================================
    # NEW ROUTES
    # ======================================================

    def classify_new_routes(self):

        findings = []

        for route in self.diff.get(
            "new_routes",
            []
        ):

            findings.append({

                "severity": "MEDIUM",

                "type":
                "NEW_PUBLIC_API",

                "reason":
                "New route exposed",

                "route":
                route.get("path"),

                "method":
                route.get("method")
            })

        return findings

    # ======================================================
    # REMOVED ROUTES
    # ======================================================

    def classify_removed_routes(self):

        findings = []

        for route in self.diff.get(
            "removed_routes",
            []
        ):

            findings.append({

                "severity": "HIGH",

                "type":
                "BREAKING_API_CHANGE",

                "reason":
                "Public API route removed",

                "route":
                route.get("path"),

                "method":
                route.get("method")
            })

        return findings

    # ======================================================
    # DATABASE CHANGES
    # ======================================================

    def classify_db_changes(self):

        findings = []

        for db in self.diff.get(
            "new_db_operations",
            []
        ):

            findings.append({

                "severity": "HIGH",

                "type":
                "DATABASE_CHANGE",

                "reason":
                "New database operation detected",

                "operation":
                db.get("operation"),

                "model":
                db.get("model"),

                "query":
                db.get("query")
            })

        return findings

    # ======================================================
    # EXECUTION FLOW CHANGES
    # ======================================================

    def classify_execution_changes(self):

        findings = []

        for edge in self.diff.get(
            "new_execution_edges",
            []
        ):

            findings.append({

                "severity": "MEDIUM",

                "type":
                "NEW_EXECUTION_PATH",

                "reason":
                "New execution dependency detected",

                "edge_type":
                edge.get("type"),

                "from":
                edge.get("from"),

                "to":
                edge.get("to")
            })

        return findings