# ==========================================================
# GOVERNANCE REPORT BUILDER
# ==========================================================


class GovernanceReportBuilder:

    # ======================================================
    # BUILD REPORT
    # ======================================================

    def build(

        self,

        governance_results
    ):

        report_lines = []

        report_lines.append(
            "=" * 80
        )

        report_lines.append(
            "AI GOVERNANCE REPORT"
        )

        report_lines.append(
            "=" * 80
        )

        for index, result in enumerate(

            governance_results,

            start=1
        ):

            governance = result.get(
                "governance",
                {}
            )

            patch = result.get(
                "patch",
                {}
            )

            findings = governance.get(
                "findings",
                []
            )

            summary = governance.get(
                "governance_summary",
                {}
            )

            # ==================================================
            # HEADER
            # ==================================================

            report_lines.append("\n")

            report_lines.append(
                f"PATCH #{index}"
            )

            report_lines.append(
                "-" * 80
            )

            report_lines.append(

                f"FILE: "
                f"{patch.get('file', 'UNKNOWN')}"
            )

            report_lines.append(

                f"FUNCTION: "
                f"{patch.get('function', 'UNKNOWN')}"
            )

            # ==================================================
            # STATUS
            # ==================================================

            report_lines.append("\nSTATUS")

            report_lines.append(
                "-" * 80
            )

            report_lines.append(

                f"Final Status: "
                f"{governance.get('final_status')}"
            )

            report_lines.append(

                f"Risk Level: "
                f"{governance.get('risk_level')}"
            )

            report_lines.append(

                f"Safe To Apply: "
                f"{governance.get('safe_to_apply')}"
            )

            report_lines.append(

                f"Recommended Action: "
                f"{governance.get('recommended_action')}"
            )

            # ==================================================
            # GOVERNANCE SUMMARY
            # ==================================================

            report_lines.append("\nSUMMARY")

            report_lines.append(
                "-" * 80
            )

            for key, value in summary.items():

                pretty_key = (
                    key.replace("_", " ")
                    .title()
                )

                report_lines.append(
                    f"{pretty_key}: {value}"
                )

            # ==================================================
            # FINDINGS
            # ==================================================

            report_lines.append("\nFINDINGS")

            report_lines.append(
                "-" * 80
            )

            if not findings:

                report_lines.append(
                    "No findings detected"
                )

            else:

                for finding in findings:

                    finding_type = finding.get(
                        "type",
                        "UNKNOWN"
                    )

                    severity = finding.get(
                        "severity",
                        "UNKNOWN"
                    )

                    message = finding.get(
                        "message",
                        "No message"
                    )

                    report_lines.append(

                        f"[{severity}] "
                        f"{finding_type}: "
                        f"{message}"
                    )

            # ==================================================
            # PATCH CONTENT
            # ==================================================

            report_lines.append("\nPATCH")

            report_lines.append(
                "-" * 80
            )

            report_lines.append(

                patch.get(
                    "patch",
                    "No patch"
                )
            )

            report_lines.append("\n")

        return "\n".join(
            report_lines
        )