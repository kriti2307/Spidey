"""
Freshness / Information-Staleness detector - orchestration layer.

Part of the AI-discoverability audit toolkit freshness skill. This is the skill's entrypoint script: it wires freshness_extraction.py's parsing helpers together with
freshness_checks.py's FRxxx check functions and runs them across one or
more related resources (a page, a linked PDF, other pages, a sitemap).

See freshness_extraction.py for how facts/dates/snapshots are extracted,
and freshness_checks.py for what each FRxxx check looks for and why.

No new dependencies are introduced beyond the project's existing
requests / BeautifulSoup / pypdf.
"""

import json
from datetime import date
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from freshness_extraction import (
    _get_visible_text,
    _extract_pdf_text,
    extract_structured_dates,
    find_facts,
    compute_snapshot,
)
from freshness_checks import (
    check_expired_deadline,
    check_expired_event,
    check_stale_time_sensitive_statement,
    check_stale_copyright,
    check_structured_vs_visible,
    check_expired_offer,
    check_fake_freshness_signal,
    check_cross_resource_conflict,
    check_sitemap_signals,
    check_sitemap_vs_page_freshness,
    check_no_real_change_since_freshness_claim,
    check_metadata_only_change,
    check_unsignaled_content_change,
)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _load_source(source):
    """Return (visible_text, structured_dates) for one source dict."""
    stype = source.get("type", "html")
    content = source["content"]

    if stype == "html":
        return _get_visible_text(content), extract_structured_dates(content)
    if stype == "pdf":
        return _extract_pdf_text(content), []
    return str(content), []  # "text"


def audit_freshness(sources, today=None, sitemap_entries=None):
    """Run the freshness/staleness audit across one or more related resources.

    sources: list of dicts, each:
        {
          "url": str,
          "label": str,            # short name, e.g. "Homepage", "Brochure PDF"
          "type": "html" | "pdf" | "text",
          "content": str | bytes,  # HTML string, raw PDF bytes/path, or plain text
        }
    Every item participates in cross-resource comparison (FR004); there is
    no special "primary" item required - pass whatever resources you want
    cross-checked against each other.

    today: optional date override for testing. Defaults to date.today().

    sitemap_entries: optional list of {"url": str, "lastmod": str} pulled
    from sitemap.xml. When provided, enables FR008/FR009 (sitemap-only
    plausibility checks) and FR012 (sitemap vs. per-page freshness signal,
    for any source whose url also appears in the sitemap).

    Each item in `sources` may also carry an optional "previous_snapshot"
    key - a dict previously returned by compute_snapshot() for that same
    URL, supplied by whatever orchestrates repeat audits of this site
    (this module does not persist snapshots itself). When present (and
    the source is type "html"), enables FR013/FR014/FR015 - snapshot-diff
    checks that compare actual text/metadata change against what the
    freshness signals claim. After a run, call compute_snapshot() on each
    html source yourself and persist the result to pass in as next time's
    previous_snapshot.

    Returns a list of finding dicts: id, title, type, severity, confidence,
    evidence, suggested_action {summary, priority}.
    """
    if today is None:
        today = date.today()

    all_facts = []
    findings = []

    for source in sources:
        label = source.get("label") or source.get("url") or "source"
        url = source.get("url", "")

        text, structured_dates = _load_source(source)
        facts = find_facts(text, label, url)
        all_facts.extend(facts)

        findings.extend(check_expired_deadline(facts, today))
        findings.extend(check_expired_event(facts, today))
        findings.extend(check_stale_time_sensitive_statement(facts, today))
        findings.extend(check_stale_copyright(text, label, url, today))
        if structured_dates:
            findings.extend(check_structured_vs_visible(structured_dates, facts, label, url))
            findings.extend(check_expired_offer(structured_dates, facts, label, url, today))
            findings.extend(check_fake_freshness_signal(structured_dates, facts, label, url, today))
        if sitemap_entries:
            findings.extend(check_sitemap_vs_page_freshness(sitemap_entries, structured_dates, facts, label, url, today))

        previous_snapshot = source.get("previous_snapshot")
        if previous_snapshot and source.get("type", "html") == "html":
            current_snapshot = compute_snapshot(source["content"], url, today)
            findings.extend(check_no_real_change_since_freshness_claim(previous_snapshot, current_snapshot, label, url))
            findings.extend(check_metadata_only_change(previous_snapshot, current_snapshot, label, url))
            findings.extend(check_unsignaled_content_change(previous_snapshot, current_snapshot, label, url))

    findings.extend(check_cross_resource_conflict(all_facts))
    if sitemap_entries:
        findings.extend(check_sitemap_signals(sitemap_entries, today))

    return findings


def audit_freshness_single(html: str, url: str) -> list:
    """Convenience wrapper matching the audit_structured_data(html, url)
    signature used elsewhere in the project, for when you only have a
    single HTML page and no related resources to cross-check against."""
    return audit_freshness([{"url": url, "label": url, "type": "html", "content": html}])


if __name__ == "__main__":
    with open("test.html", "r", encoding="utf-8") as f:
        html = f.read()

    results = audit_freshness_single(html, "https://example.com")

    if results:
        print(json.dumps({"status": "issues_found", "findings": results}, indent=2, default=str))
    else:
        print(json.dumps({
            "status": "pass",
            "message": "No freshness issues detected.",
            "findings": [],
        }, indent=2))