# ==========================================================
# REVIEW PROMPT BUILDER
# ==========================================================

class ReviewPromptBuilder:

    # ======================================================
    # BUILD PROMPT
    # ======================================================

    def build_prompt(

        self,

        impact_result,

        context_result,

        changes=None
    ):

        lines = []

        # ==================================================
        # SYSTEM ROLE
        # ==================================================

        lines.append(
            "You are an expert senior software engineer and security reviewer."
        )

        lines.append(
            "Analyze the following semantic code impact carefully."
        )

        lines.append(
            "Focus on:"
        )

        lines.append(
            "- regressions"
        )

        lines.append(
            "- security vulnerabilities"
        )

        lines.append(
            "- architecture problems"
        )

        lines.append(
            "- downstream impact"
        )

        lines.append(
            "- unsafe propagation"
        )

        lines.append(
            "- maintainability concerns"
        )

        lines.append("")

        # ==================================================
        # IMPACT SUMMARY
        # ==================================================

        lines.append(
            "=================================================="
        )

        lines.append(
            "IMPACT SUMMARY"
        )

        lines.append(
            "=================================================="
        )

        lines.append("")

        # ==================================================
        # ROUTES
        # ==================================================

        affected_routes = impact_result.get(

            "affected_routes",

            []
        )

        if affected_routes:

            lines.append(
                "Affected Routes:"
            )

            for route in affected_routes:

                method = route.get(
                    "method"
                )

                path = route.get(
                    "route"
                )

                lines.append(

                    f"- [{method}] {path}"
                )

            lines.append("")

        # ==================================================
        # FUNCTIONS
        # ==================================================

        affected_functions = impact_result.get(

            "affected_functions",

            []
        )

        if affected_functions:

            lines.append(
                "Affected Functions:"
            )

            for func in affected_functions:

                lines.append(

                    f"- {func.get('file')} :: "
                    f"{func.get('function')}"
                )

            lines.append("")

        # ==================================================
        # DATABASE IMPACT
        # ==================================================

        database_impact = impact_result.get(

            "database_impact",

            []
        )

        if database_impact:

            lines.append(
                "Database Impact:"
            )

            for db in database_impact:

                lines.append(

                    f"- Model: "
                    f"{db.get('model')} | "
                    f"Operation: "
                    f"{db.get('operation')}"
                )

            lines.append("")

        # ==================================================
        # SECURITY IMPACT
        # ==================================================

        security_impact = impact_result.get(

            "security_impact",

            []
        )

        if security_impact:

            lines.append(
                "Security Findings:"
            )

            for finding in security_impact:

                lines.append(

                    f"- {finding.get('type')}"
                )

            lines.append("")

        # ==================================================
        # EXECUTION CHAIN
        # ==================================================

        execution_chain = context_result.get(

            "execution_chain",

            []
        )

        if execution_chain:

            lines.append(
                "Execution Chain:"
            )

            for item in execution_chain:

                # ==============================================
                # ROUTE
                # ==============================================

                if item.get("type") == "ROUTE":

                    lines.append(

                        f"- Route [{item.get('method')}] "
                        f"{item.get('route')} "
                        f"→ {item.get('target_function')}"
                    )

                # ==============================================
                # FUNCTION CALL
                # ==============================================

                elif (

                    item.get("type")

                    ==

                    "FUNCTION_CALL"
                ):

                    lines.append(

                        f"- {item.get('caller_function')}() "
                        f"→ {item.get('target_function')}()"
                    )

            lines.append("")


        # ==================================================
        # ROUTE CONTEXT
        # ==================================================

        route_context = context_result.get(

            "route_context",

            []
        )

        if route_context:

            lines.append(
                "Route Context:"
            )

            for route in route_context:

                lines.append(

                    f"- [{route.get('method')}] "
                    f"{route.get('route')}"
                )

            lines.append("")


        # ==================================================
        # TAINT FLOW
        # ==================================================

        taint_flow = context_result.get(

            "taint_flow",

            []
        )

        if taint_flow:

            lines.append(
                "Taint Flow:"
            )

            for taint in taint_flow:
                # ==============================================
                # USER INPUT FLOW
                # ==============================================

                if taint.get("type") == "USER_INPUT":

                    lines.append(

                        f"- {taint.get('source')} "
                        f"→ "
                        f"{taint.get('target_function')}("
                        f"{taint.get('target_param')})"
                    )

                # ==============================================
                # RETURN TAINT
                # ==============================================

                elif taint.get("type") == "RETURN_TAINT":

                    lines.append(

                        f"- RETURN "
                        f"{taint.get('source')} "
                        f"from "
                        f"{taint.get('target_function')}()"
                    )
                # lines.append(

                #     f"- {taint.get('source')} "
                #     f"→ "
                #     f"{taint.get('target_function')}("
                #     f"{taint.get('target_param')})"
                # )

            lines.append("")

        # ==================================================
        # CODE CONTEXT
        # ==================================================

        lines.append(
            "=================================================="
        )

        lines.append(
            "RELEVANT CODE"
        )

        lines.append(
            "=================================================="
        )

        lines.append("")

        snippets = context_result.get(

            "code_snippets",

            []
        )

        for snippet in snippets:

            file_path = snippet.get(
                "file"
            )

            function_name = snippet.get(
                "function"
            )

            code = snippet.get(
                "code"
            )

            lines.append(
                f"FILE: {file_path}"
            )

            lines.append(
                f"FUNCTION: {function_name}"
            )

            lines.append("")

            lines.append("```javascript")

            lines.append(code)

            lines.append("```")

            lines.append("")


        # ==================================================
        # DIFF CONTEXT
        # ==================================================

        if changes:

            lines.append("")

            lines.append(
                "=================================================="
            )

            lines.append(
                "SEMANTIC DIFF"
            )

            lines.append(
                "=================================================="
            )

            for hunk in changes.get(

                "diff_hunks",

                []
            ):

                lines.append("")

                lines.append(
                    f"FILE: {hunk['file']}"
                )

                lines.append("")

                lines.append("REMOVED:")

                for line in hunk["removed"]:

                    lines.append(
                        f"- {line}"
                    )

                lines.append("")

                lines.append("ADDED:")

                for line in hunk["added"]:

                    lines.append(
                        f"+ {line}"
                    )

        # ==================================================
        # REVIEW INSTRUCTIONS
        # ==================================================

        lines.append(
            "=================================================="
        )


        lines.append(
            "REVIEW TASK"
        )


        lines.append(
            "=================================================="
        )

        lines.append("")

        lines.append(
            "Provide a detailed review covering:"
        )

        lines.append(
            "1. Security risks"
        )

        lines.append(
            "2. Regression risks"
        )

        lines.append(
            "3. Architecture concerns"
        )

        lines.append(
            "4. Data flow risks"
        )

        lines.append(
            "5. Suggested fixes"
        )

        lines.append("")

        lines.append(
            "Be precise and technical."
        )
        lines.append("")

        lines.append(
            "Return the review ONLY as valid JSON."
        )

        lines.append(
            "Do not include markdown explanations."
        )

        lines.append(
            "Return a JSON array."
        )

        lines.append(
            "Each review item must contain:"
        )

        lines.append(
            "- severity"
        )

        lines.append(
            "- category"
        )

        lines.append(
            "- title"
        )

        lines.append(
            "- description"
        )

        lines.append(
            "- recommendation"
        )

        lines.append(
            "- affected_function"
        )

        lines.append(
            "- confidence"
        )

        lines.append("")

        lines.append(
            "Example:"
        )

        lines.append("")

        lines.append(
            '[{"severity":"HIGH","category":"DATA_LEAK","title":"Sensitive data exposure","description":"User password flows into unsafe return path","recommendation":"Sanitize or remove password propagation","affected_function":"fetchUsers","confidence":0.92}]'
        )

        # ==================================================
        # FINAL PROMPT
        # ==================================================

        return "\n".join(lines)