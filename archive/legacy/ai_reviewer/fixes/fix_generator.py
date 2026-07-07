# ==========================================================
# FIX GENERATOR
# ==========================================================

import json

import re


class FixGenerator:

    # ======================================================
    # INIT
    # ======================================================

    def __init__(

        self,

        reviewer
    ):

        self.reviewer = reviewer

    # ======================================================
    # GENERATE FIXES
    # ======================================================

    def generate_fixes(

        self,

        review_results,

        context_result,

        changes
    ):

        prompt = self.build_fix_prompt(

            review_results=review_results,

            context_result=context_result,

            changes=changes
        )

        raw_response = (
            self.reviewer.generate_review(
                prompt
            )
        )

        return self.parse_fix_response(
            raw_response
        )

    # ======================================================
    # BUILD FIX PROMPT
    # ======================================================

    def build_fix_prompt(

        self,

        review_results,

        context_result,

        changes
    ):

        lines = []

        # ==================================================
        # SYSTEM ROLE
        # ==================================================

        lines.append(
            "You are an expert senior software engineer."
        )

        lines.append(
            "Generate secure and minimal code fixes."
        )

        lines.append(
            "Do not rewrite unrelated logic."
        )

        lines.append(
            "Return ONLY valid JSON."
        )

        lines.append("")

        # ==================================================
        # REVIEW FINDINGS
        # ==================================================

        lines.append(
            "=================================================="
        )

        lines.append(
            "REVIEW FINDINGS"
        )

        lines.append(
            "=================================================="
        )

        for finding in review_results:

            lines.append("")

            lines.append(
                f"Severity: {finding.get('severity')}"
            )

            lines.append(
                f"Category: {finding.get('category')}"
            )

            lines.append(
                f"Title: {finding.get('title')}"
            )

            lines.append(
                f"Description: {finding.get('description')}"
            )

            lines.append(
                f"Recommendation: {finding.get('recommendation')}"
            )

        # ==================================================
        # DIFF CONTEXT
        # ==================================================

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
        # RELEVANT CODE
        # ==================================================

        lines.append("")

        lines.append(
            "=================================================="
        )

        lines.append(
            "RELEVANT CODE"
        )

        lines.append(
            "=================================================="
        )

        # for item in context_result:

        #     lines.append("")

        #     lines.append(
        #         f"FILE: {item['file']}"
        #     )

        #     lines.append(
        #         f"FUNCTION: {item['function']}"
        #     )

        #     lines.append("")

        #     lines.append("```javascript")

        #     lines.append(
        #         item["code"]
        #     )

        #     lines.append("```")

        # ==================================================
        # NORMALIZE CONTEXT
        # ==================================================

        normalized_context = []

        if isinstance(

            context_result,

            dict
        ):

            # ==============================================
            # dict with contexts key
            # ==============================================

            if "contexts" in context_result:

                normalized_context = (
                    context_result["contexts"]
                )

            # ==============================================
            # single object
            # ==============================================

            else:

                normalized_context = [
                    context_result
                ]

        elif isinstance(

            context_result,

            list
        ):

            normalized_context = (
                context_result
            )

        # ==================================================
        # ITERATE CONTEXT
        # ==================================================

        for item in normalized_context:

            # ==============================================
            # SKIP INVALID ITEMS
            # ==============================================

            if not isinstance(item, dict):

                continue

            lines.append("")

            lines.append(
                f"FILE: {item.get('file')}"
            )

            lines.append(
                f"FUNCTION: {item.get('function')}"
            )

            lines.append("")

            lines.append("```javascript")

            lines.append(
                item.get("code", "")
            )

            lines.append("```")

        # ==================================================
        # FIX TASK
        # ==================================================

        lines.append("")

        lines.append(
            "=================================================="
        )

        lines.append(
            "FIX TASK"
        )

        lines.append(
            "=================================================="
        )

        lines.append(
            "Generate minimal secure patches."
        )

        lines.append(
            "Preserve business logic."
        )

        lines.append(
            "Do not modify unrelated code."
        )

        lines.append(
            "Return ONLY valid JSON array."
        )

        lines.append(
            "Each patch must contain:"
        )

        lines.append(
            "- file"
        )

        lines.append(
            "- function"
        )

        lines.append(
            "- risk"
        )

        lines.append(
            "- patch"
        )

        lines.append(
            "- explanation"
        )

        lines.append("")

        lines.append(
            "Example:"
        )

        lines.append("")

        lines.append(
            '[{"file":"services/userService.js","function":"fetchUsers","risk":"Password exposure","patch":"- return password;\\n+ return email;","explanation":"Removes sensitive password leakage"}]'
        )

        return "\n".join(lines)



    # ======================================================
    # NORMALIZE LLM PATCH OUTPUT
    # ======================================================

    def normalize_llm_patch_output(

        self,

        raw_response
    ):

        if not raw_response:

            return ""

        cleaned = raw_response.strip()

        # ==================================================
        # REMOVE ```json
        # ==================================================

        cleaned = re.sub(

            r"^```json",

            "",

            cleaned,

            flags=re.IGNORECASE
        )

        # ==================================================
        # REMOVE ```
        # ==================================================

        cleaned = re.sub(

            r"```$",

            "",

            cleaned
        )

        cleaned = cleaned.strip()

        # ==================================================
        # EXTRACT JSON ARRAY
        # ==================================================

        match = re.search(

            r"(\[.*\])",

            cleaned,

            re.DOTALL
        )

        if match:

            cleaned = match.group(1)

        return cleaned


    # ======================================================
    # PARSE FIX RESPONSE
    # ======================================================

    def parse_fix_response(

        self,

        raw_response
    ):

        try:

            # return json.loads(
            #     raw_response
            # )
            normalized = (
                self.normalize_llm_patch_output(
                    raw_response
                )
            )

            return json.loads(
                normalized
            )

        except Exception as e:
            return [

                {
                    "risk":
                        "FIX_PARSE_ERROR",

                    "error":
                        str(e),

                    "raw_response":
                        raw_response
                }
            ]