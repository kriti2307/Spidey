from pathlib import Path
from collections import defaultdict


TYPE_LABELS = {
    "issue": "Issue",
    "warning": "Warning",
    "opportunity": "Opportunity",
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def get_url_from_evidence(evidence):
    """
    Evidence is currently normalized like:
    https://example.com/page — actual evidence text
    """
    evidence = str(evidence)

    if " — " in evidence:
        url, rest = evidence.split(" — ", 1)
        if url.startswith(("http://", "https://")):
            return url, rest

    return None, evidence


def group_findings(findings):
    """
    Group repeated findings that describe the same underlying problem.

    Example:
    - Missing H1 on /about-us
    - Missing H1 on /speakers
    - Missing H1 on /publication

    become ONE report item with multiple affected pages.
    """

    groups = {}

    for finding in findings:
        key = (
            finding.get("type", "issue"),
            finding.get("title", "Unnamed finding"),
            finding.get("severity", "medium"),
        )

        if key not in groups:
            groups[key] = {
                "type": finding.get("type", "issue"),
                "title": finding.get(
                    "title",
                    "Unnamed finding"
                ),
                "severity": finding.get(
                    "severity",
                    "medium"
                ),
                "priority": (
                    finding.get(
                        "suggested_action",
                        {}
                    ).get(
                        "priority",
                        finding.get(
                            "severity",
                            "medium"
                        )
                    )
                    if isinstance(
                        finding.get("suggested_action"),
                        dict
                    )
                    else finding.get(
                        "severity",
                        "medium"
                    )
                ),
                "findings": [],
            }

        groups[key]["findings"].append(finding)

    return list(groups.values())


def render_grouped_evidence(group):
    """
    Produce a readable 'where it was found' section.
    """

    lines = []

    affected = []

    for finding in group["findings"]:
        url, evidence = get_url_from_evidence(
            finding.get("evidence", "")
        )

        if url:
            affected.append(url)

        lines.append(
            f"- {url if url else 'Unknown page'} — {evidence}"
        )

    unique_urls = list(dict.fromkeys(affected))

    return unique_urls, lines


def render_markdown(report: dict) -> str:
    site = report.get(
        "site",
        "Unknown site"
    )

    audited_at = report.get(
        "audited_at",
        "Unknown"
    )

    summary = report.get(
        "summary",
        {}
    )

    findings = report.get(
        "findings",
        []
    )

    groups = group_findings(findings)

    groups.sort(
        key=lambda group: (
            SEVERITY_ORDER.get(
                str(group["severity"]).lower(),
                99
            ),
            -len(group["findings"]),
        )
    )

    lines = []

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------

    lines.append(
        "# Brand AI-Readiness Audit"
    )
    lines.append("")

    lines.append(
        f"**Site:** `{site}`"
    )

    lines.append(
        f"**Audited at:** `{audited_at}`"
    )

    lines.append("")
    lines.append("---")
    lines.append("")

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    lines.append("## Summary")
    lines.append("")

    lines.append(
        f"**Total findings:** "
        f"{summary.get('total_findings', 0)}"
    )

    lines.append("")

    lines.append(
        f"🔴 Critical: **{summary.get('critical', 0)}**  \n"
        f"🟠 High: **{summary.get('high', 0)}**  \n"
        f"🟡 Medium: **{summary.get('medium', 0)}**  \n"
        f"🟢 Low: **{summary.get('low', 0)}**"
    )

    lines.append("")

    # ---------------------------------------------------------
    # NO FINDINGS
    # ---------------------------------------------------------

    if not groups:
        lines.append("## Result")
        lines.append("")
        lines.append(
            "✅ No audit findings were detected."
        )
        return "\n".join(lines)

    # ---------------------------------------------------------
    # TOP PRIORITIES
    # ---------------------------------------------------------

    lines.append("## Top Priorities")
    lines.append("")

    # Only one entry per grouped problem.
    for index, group in enumerate(
        groups[:3],
        start=1
    ):
        severity = str(
            group["severity"]
        ).lower()

        icon = SEVERITY_ICONS.get(
            severity,
            "⚪"
        )

        title = group["title"]
        affected_count = len(
            group["findings"]
        )

        lines.append(
            f"{index}. {icon} **{title}** — "
            f"`{severity.title()}` "
            f"({affected_count} affected)"
        )

    lines.append("")

    # ---------------------------------------------------------
    # FINDINGS
    # ---------------------------------------------------------

    lines.append("## Findings")
    lines.append("")

    for index, group in enumerate(
        groups,
        start=1
    ):
        severity = str(
            group["severity"]
        ).lower()

        finding_type = str(
            group["type"]
        ).lower()

        icon = SEVERITY_ICONS.get(
            severity,
            "⚪"
        )

        type_label = TYPE_LABELS.get(
            finding_type,
            finding_type.title()
        )

        title = group["title"]

        unique_urls, evidence_lines = (
            render_grouped_evidence(group)
        )

        # Use the first finding's action
        first_finding = group["findings"][0]

        action = first_finding.get(
            "suggested_action",
            {}
        )

        if not isinstance(action, dict):
            action = {
                "summary": str(action)
            }

        action_summary = action.get(
            "summary",
            "Review and resolve this finding."
        )

        priority = str(
            action.get(
                "priority",
                severity
            )
        ).lower()

        steps = action.get(
            "steps",
            []
        )

        lines.append(
            f"### {index}. {icon} {title}"
        )

        lines.append("")

        lines.append(
            f"**Type:** `{type_label}`"
        )

        lines.append(
            f"**Severity:** `{severity.title()}`"
        )

        lines.append(
            f"**Affected pages/resources:** "
            f"{len(unique_urls)}"
        )

        lines.append("")

        # -----------------------------------------------------
        # WHERE IT WAS FOUND
        # -----------------------------------------------------

        lines.append(
            "#### Where it was found"
        )

        lines.append("")

        for url in unique_urls:
            lines.append(
                f"- `{url}`"
            )

        lines.append("")

        # -----------------------------------------------------
        # EVIDENCE
        # -----------------------------------------------------

        lines.append(
            "#### Evidence"
        )

        lines.append("")

        for evidence in evidence_lines:
            lines.append(
                f"> {evidence[2:]}"
            )

        lines.append("")

        # -----------------------------------------------------
        # SUGGESTED ACTION
        # -----------------------------------------------------

        lines.append(
            "#### Suggested Action"
        )

        lines.append("")

        lines.append(
            action_summary
        )

        lines.append("")

        if steps:
            lines.append(
                "**Steps:**"
            )

            lines.append("")

            for step in steps:
                lines.append(
                    f"- {step}"
                )

            lines.append("")

        lines.append(
            f"**Priority:** `{priority.title()}`"
        )

        lines.append("")

        lines.append("---")
        lines.append("")

    # ---------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------

    lines.append(
        "_This report is recommendation-only. "
        "No changes were made to the audited website._"
    )

    return "\n".join(lines)


def save_markdown(
    report: dict,
    output_path: str
) -> None:
    markdown = render_markdown(
        report
    )

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        markdown,
        encoding="utf-8"
    )
