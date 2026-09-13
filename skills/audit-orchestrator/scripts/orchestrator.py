import sys
import json
from datetime import datetime, timezone
import os
from report_renderer import save_markdown


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
    Convert a specialist finding into Adobe's required format
    while preserving useful fields such as type and steps.
    """

    severity = str(
        finding.get("severity", "medium")
    ).lower()

    if severity not in SEVERITIES:
        severity = "medium"

    finding_type = str(
        finding.get("type", "issue")
    ).lower()

    if finding_type not in {
        "issue",
        "warning",
        "opportunity"
    }:
        finding_type = "issue"

    recommendation = finding.get(
        "recommendation",
        finding.get("suggested_action", {})
    )

    if isinstance(recommendation, dict):

        action_summary = recommendation.get(
            "summary",
            "Review and resolve this issue."
        )

        priority = str(
            recommendation.get(
                "priority",
                severity
            )
        ).lower()

        steps = recommendation.get(
            "steps",
            []
        )

    else:

        action_summary = str(
            recommendation or
            "Review and resolve this issue."
        )

        priority = severity
        steps = []

    if priority not in SEVERITIES:
        priority = severity

    evidence = normalize_evidence(
        finding.get("evidence")
    )

    # Include the affected URL in the evidence
    url = finding.get("url")

    if url:
        evidence = f"{url} — {evidence}"

    suggested_action = {
        "summary": action_summary,
        "priority": priority
    }

    # Preserve detailed mechanism-specific fix steps
    if steps:
        suggested_action["steps"] = steps

    return {
        "id": finding_id,

        "type": finding_type,

        "title": finding.get(
            "title",
            "Unnamed audit finding"
        ),

        "severity": severity,

        "evidence": evidence,

        "suggested_action": suggested_action
    }


def build_report(site, specialist_findings):
    """
    Combine findings from all specialist skills
    into Adobe's required audit report schema.
    """

    findings = []
    seen_findings = set()

    for finding in specialist_findings:

        normalized = normalize_finding(
            finding,
            f"F-{len(findings) + 1:03d}"
        )

        # Deduplicate identical findings
        dedupe_key = (
            normalized["title"],
            normalized["severity"],
            normalized["evidence"]
        )

        if dedupe_key in seen_findings:
            continue

        seen_findings.add(dedupe_key)
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

        for finding in page_findings:

            # Force the source URL into every finding
            finding["url"] = url

            findings.append(finding)

    return findings


def run_freshness_audit(crawl_audit):
    """
    Run the freshness specialist against HTML already
    collected by crawlability.
    """

    from pathlib import Path
    import importlib.util

    skills_root = Path(__file__).resolve().parents[2]

    freshness_path = (
        skills_root
        / "freshness"
        / "scripts"
        / "freshness_audit.py"
    )

    spec = importlib.util.spec_from_file_location(
        "freshness_audit",
        freshness_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    findings = []

    for page in crawl_audit.get("pages", []):

        html = page.get("html")
        url = page.get("url")

        if not html or not url:
            continue

        page_findings = module.audit_freshness_single(
            html,
            url
        )

        for finding in page_findings:

            # Attach the source URL so the orchestrator
            # can include it in Adobe evidence.
            finding["url"] = url

            findings.append(finding)

    return findings


def run_non_text_audit(crawl_audit):
    """
    Run the non-text specialist against HTML already
    collected by crawlability.
    """

    from pathlib import Path
    import importlib.util

    skills_root = Path(__file__).resolve().parents[2]

    non_text_path = (
        skills_root
        / "non-text"
        / "scripts"
        / "non_text_audit.py"
    )

    spec = importlib.util.spec_from_file_location(
        "non_text_audit",
        non_text_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    findings = []

    for page in crawl_audit.get("pages", []):

        html = page.get("html")
        url = page.get("url")

        if not html or not url:
            continue

        page_findings = module.audit_non_text(
            html,
            url
        )

        for finding in page_findings:

            # Attach source URL for Adobe evidence
            finding["url"] = url

            findings.append(finding)

    return findings


def run_engagement_audit(site_url, crawl_audit):
    """
    Run the engagement specialist only when the homepage
    was successfully crawled.
    """

    homepage = None

    for page in crawl_audit.get("pages", []):
        if page.get("url") == site_url or page.get("finalUrl") == site_url:
            homepage = page
            break

    if not homepage or not homepage.get("success"):
        return []

    from pathlib import Path
    import importlib.util

    skills_root = Path(__file__).resolve().parents[2]

    engagement_path = (
        skills_root
        / "engagement-audit"
        / "engagement_audit.py"
    )

    spec = importlib.util.spec_from_file_location(
        "engagement_audit",
        engagement_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    report = module.run_audit(
    site_url,
    crawl_audit=crawl_audit
)

    findings = report.get("findings", [])

    for finding in findings:
        if not finding.get("url"):
            finding["url"] = site_url

    return findings


def main():
    import subprocess
    import os

    if len(sys.argv) < 2:
        print(
            "Usage: python orchestrator.py <url>",
            file=sys.stderr
        )
        sys.exit(1)

    site_url = sys.argv[1]

    crawler_path = os.path.join(
        os.path.dirname(__file__),
        "../../crawlability/scripts/crawler/crawler.js"
    )

    crawler_path = os.path.abspath(crawler_path)

    env = os.environ.copy()
    env["CRAWL_JSON"] = "1"

    result = subprocess.run(
        [
            "node",
            crawler_path,
            site_url,
            "20"
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

    # Freshness findings
    freshness_findings = run_freshness_audit(crawl_audit)
    specialist_findings.extend(freshness_findings)

    non_text_findings = run_non_text_audit(crawl_audit)
    specialist_findings.extend(non_text_findings)

    # -----------------------------
    # Engagement audit findings
    # -----------------------------
    engagement_findings = run_engagement_audit(
        crawl_audit["site"],
        crawl_audit
    )

    specialist_findings.extend(engagement_findings)

    # -----------------------------
    # Build Adobe report
    # -----------------------------

    report = build_report(
        crawl_audit["site"],
        specialist_findings
    )

    # Save human-readable Markdown report
    report_path = os.path.join(
        os.getcwd(),
        "audit-report.md"
    )

    save_markdown(
        report,
        report_path
    )

    # Print canonical JSON report
    print(
        json.dumps(
            report,
            indent=2
        )
    )

    print(
        f"\nHuman-readable report saved to: {report_path}",
        file=sys.stderr
    )


if __name__ == "__main__":
    main()