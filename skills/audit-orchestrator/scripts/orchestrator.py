import sys
import json
from datetime import datetime, timezone
import os


SEVERITIES = ["critical", "high", "medium", "low"]


def normalize_evidence(evidence):
    """
    Adobe requires evidence to be a string.
    Our specialist skills may return a string or list.
    """
    if isinstance(evidence, list):
        return " ".join(str(item) for item in evidence)

    if evidence is None:
        return "No evidence provided."

    return str(evidence)


def normalize_finding(finding, finding_id):
    """
    Convert a specialist finding into Adobe's required format.
    """

    severity = str(
        finding.get("severity", "medium")
    ).lower()

    if severity not in SEVERITIES:
        severity = "medium"

    recommendation = finding.get(
        "recommendation",
        finding.get("suggested_action", "")
    )

    if isinstance(recommendation, dict):

        action_summary = recommendation.get(
            "summary",
            "Review and resolve this issue."
        )

        priority = recommendation.get(
            "priority",
            severity
        )

    else:

        action_summary = str(
            recommendation or
            "Review and resolve this issue."
        )

        priority = severity

    # Normalize evidence
    evidence = normalize_evidence(
        finding.get("evidence")
    )

    # Include the affected URL in the evidence
    # so the final Adobe report clearly identifies
    # which page produced the finding.
    url = finding.get("url")

    if url:
        evidence = f"{url} — {evidence}"

    return {
        "id": finding_id,

        "title": finding.get(
            "title",
            "Unnamed audit finding"
        ),

        "severity": severity,

        "evidence": evidence,

        "suggested_action": {
            "summary": action_summary,
            "priority": priority
        }
    }


def build_report(site, specialist_findings):
    """
    Combine findings from all specialist skills
    into Adobe's required audit report schema.
    """

    findings = []

    for finding in specialist_findings:

        normalized = normalize_finding(
            finding,
            f"F-{len(findings) + 1:03d}"
        )

        findings.append(normalized)

    summary = {
        "total_findings": len(findings),
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0
    }

    for finding in findings:
        severity = finding["severity"]

        if severity in summary:
            summary[severity] += 1

    return {
        "site": site,
        "audited_at": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),

        "summary": summary,

        "findings": findings
    }

def run_structured_data_audit(crawl_audit):
    """
    Run the structured-data specialist against HTML already
    collected by crawlability.
    """

    from pathlib import Path
    import importlib.util

    skills_root = Path(__file__).resolve().parents[2]

    structured_data_path = (
        skills_root
        / "structured-data"
        / "scripts"
        / "structured_data_audit.py"
    )

    spec = importlib.util.spec_from_file_location(
        "structured_data_audit",
        structured_data_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    findings = []

    for page in crawl_audit.get("pages", []):

        html = page.get("html")
        url = page.get("url")

        if not html or not url:
            continue

        page_findings = module.audit_structured_data(
            html,
            url
        )

        # The structured-data skill doesn't always include
        # the page URL in its finding.
        # The orchestrator knows the URL, so attach it here.
        for finding in page_findings:

            if not finding.get("url"):
                finding["url"] = url

            findings.append(finding)

    return findings

def run_structured_data_audit(crawl_audit):

    from pathlib import Path
    import importlib.util

    skills_root = Path(__file__).resolve().parents[2]

    structured_data_path = (
        skills_root
        / "structured-data"
        / "scripts"
        / "structured_data_audit.py"
    )

    spec = importlib.util.spec_from_file_location(
        "structured_data_audit",
        structured_data_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    findings = []

    for page in crawl_audit.get("pages", []):

        html = page.get("html")
        url = page.get("url")

        if not html or not url:
            continue

        page_findings = module.audit_structured_data(
            html,
            url
        )

        findings.extend(page_findings)

    return findings


def main():

    import subprocess
    import os

    crawler_path = os.path.join(
        os.path.dirname(__file__),
        "../../crawlability/scripts/test/run-crawler-test.js"
    )

    crawler_path = os.path.abspath(crawler_path)

    env = os.environ.copy()
    env["CRAWL_JSON"] = "1"

    result = subprocess.run(
        [
            "node",
            crawler_path
        ],
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    crawl_audit = json.loads(
        result.stdout
    )

    # -----------------------------
    # Collect specialist findings
    # -----------------------------

    specialist_findings = []

    # Crawlability findings
    for page in crawl_audit.get("pages", []):

        specialist_findings.extend(
            page.get("findings", [])
        )

    # Structured-data findings
    structured_findings = run_structured_data_audit(
        crawl_audit
    )

    specialist_findings.extend(
        structured_findings
    )

    # -----------------------------
    # Build Adobe report
    # -----------------------------

    report = build_report(
        crawl_audit["site"],
        specialist_findings
    )

    print(
        json.dumps(
            report,
            indent=2
        )
    )


if __name__ == "__main__":
    main()