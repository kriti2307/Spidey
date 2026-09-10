"""
Freshness / Information-Staleness detector.

Part of the AI-discoverability audit toolkit (Adobe University Hackathon
2026, Round 3). This module ONLY detects time-sensitive information that
may be stale, expired, or inconsistent - across a single page and,
optionally, related resources (other pages, a linked PDF).

It intentionally does NOT do structured-data auditing, crawlability,
entity/reputation checks, or non-text auditing - those are separate
modules.

------------------------------------------------------------------------
WHY THIS MODULE LOOKS THE WAY IT DOES
------------------------------------------------------------------------
"Old" != "stale". A five-year-old About Us page is fine. A five-day-past
"Early bird deadline: March 1" statement that's still live on March 15 is
a real problem for anything (human or AI agent) making a decision from it.

So instead of asking "how old is this page/date", every check here asks
one of two sharper questions:

  1. Is this specific fact TIME-SENSITIVE (a deadline, an event date, a
     price, hours, availability) AND does the page's own language suggest
     it has already lapsed while still being presented as live?

  2. Do independent sources an AI agent might retrieve for the SAME fact
     (this page, another page, a linked PDF, the page's own structured
     data) DISAGREE with each other?

(2) is weighted as more interesting than (1) - a single old date is a
maybe; two live sources disagreeing about the same fact is a real
integrity problem regardless of how old either date is. This mirrors the
ACIFFS case: webpage vs. PDF brochure vs. another official page each
gave a different conference/deadline date.

No new dependencies are introduced beyond the project's existing
requests / BeautifulSoup / pypdf.
------------------------------------------------------------------------
"""

import io
import json
import re
from datetime import date, datetime

from bs4 import BeautifulSoup, Comment

try:
    from pypdf import PdfReader
except ImportError:  # pypdf is an optional dep at import time for HTML-only use
    PdfReader = None


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MONTH_NAMES = sorted(MONTHS.keys(), key=len, reverse=True)
_MONTH_RE = "|".join(_MONTH_NAMES)

# Ordered by specificity: earlier patterns claim their span first, so a
# more specific match (e.g. "March 1, 2026") wins over a looser one
# (e.g. "March 2026") that happens to overlap it.
DATE_PATTERNS = [
    (re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b'), "iso", "high"),
    (re.compile(rf'\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b', re.IGNORECASE), "month_d_y", "high"),
    (re.compile(rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})\.?,?\s+(\d{{4}})\b', re.IGNORECASE), "d_month_y", "high"),
    (re.compile(rf'\b({_MONTH_RE})\.?\s+(\d{{4}})\b', re.IGNORECASE), "month_y", "medium"),
    (re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b'), "slash", "low"),
]


def _safe_date(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except (ValueError, TypeError):
        return None


def extract_dates(text):
    """Find date-like substrings in `text`.

    Returns a list of dicts: {"date", "start", "end", "raw", "confidence"},
    sorted by position. Overlapping matches are resolved by preferring
    earlier (more specific) patterns in DATE_PATTERNS.
    """
    found = []
    claimed = []  # (start, end) spans already claimed by a higher-priority pattern

    def overlaps(s, e):
        return any(not (e <= cs or s >= ce) for cs, ce in claimed)

    for pattern, kind, confidence in DATE_PATTERNS:
        for m in pattern.finditer(text):
            s, e = m.span()
            if overlaps(s, e):
                continue

            d = None
            if kind == "iso":
                d = _safe_date(m.group(1), m.group(2), m.group(3))
            elif kind == "month_d_y":
                mon = MONTHS.get(m.group(1).lower())
                d = _safe_date(m.group(3), mon, m.group(2)) if mon else None
            elif kind == "d_month_y":
                mon = MONTHS.get(m.group(2).lower())
                d = _safe_date(m.group(3), mon, m.group(1)) if mon else None
            elif kind == "month_y":
                mon = MONTHS.get(m.group(1).lower())
                d = _safe_date(m.group(2), mon, 1) if mon else None
            elif kind == "slash":
                a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
                # Ambiguous MM/DD vs DD/MM. Prefer whichever reading is a
                # valid month; if both could be, assume MM/DD (US-style).
                if a <= 12:
                    d = _safe_date(y, a, b)
                elif b <= 12:
                    d = _safe_date(y, b, a)

            if d is None:
                continue

            claimed.append((s, e))
            found.append({"date": d, "start": s, "end": e, "raw": m.group(0), "confidence": confidence})

    found.sort(key=lambda x: x["start"])
    return found


def _parse_iso_loose(value):
    """Parse a structured-data date field (ISO 8601, possibly with a time
    component / 'Z' suffix). Falls back to the general extractor for
    non-standard values."""
    value = str(value).strip()
    try:
        v = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(v).date()
    except ValueError:
        dates = extract_dates(value)
        return dates[0]["date"] if dates else None


# ---------------------------------------------------------------------------
# Time-sensitive keyword vocabulary
# ---------------------------------------------------------------------------

FACT_KEYWORDS = {
    "deadline": [
        "submission deadline", "registration closes", "abstract submission",
        "deadline", "apply by", "register by", "due by", "closes on",
        "submissions close", "last date to apply",
    ],
    # NOTE: deliberately no bare nouns here ("conference", "summit",
    # "webinar", ...). Those name the *type* of gathering but don't
    # anchor a date claim, and in unstructured text (PDFs, plain text
    # with no tag boundaries) they tend to sit in the same clause as a
    # title or an unrelated date, causing false associations. Only
    # phrases that specifically assert a date go here.
    "event": [
        "will be held", "takes place", "scheduled for", "event date",
        "starts on", "begins on",
    ],
    "updated": [
        "updated on", "last updated", "updated:", "as of",
    ],
    "hours": [
        "opening hours", "business hours", "store hours", "open daily",
        "mon-fri", "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday",
    ],
    "price": [
        "starting at", "per night", "per person", "price",
    ],
    "availability": [
        "sold out", "out of stock", "in stock", "available now",
        "limited availability", "spots remaining", "seats left", "limited seats",
    ],
}

# Text that shows the page ALREADY acknowledges a deadline/event has
# lapsed - presence of this near a past date means "don't flag."
CLOSED_ACK_WORDS = [
    "deadline has passed", "deadline passed", "no longer accepting",
    "submissions closed", "registration closed", "now closed", "extended to",
]

# Forward-looking language that shows an event is still being promoted as
# upcoming - required (in addition to a past date) before FR002 fires.
FUTURE_LANGUAGE = [
    "will be held", "join us", "upcoming", "register now", "save the date",
    "don't miss", "see you there", "we look forward", "coming soon",
]

STALE_THRESHOLD_DAYS = 180  # for FR006 (self-declared "as of" staleness)


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _get_visible_text(html):
    """Visible page text with script/style/noscript/comments stripped, so
    keyword and date matching never picks up JSON-LD, CSS, or JS content.

    Uses "\\n" as the join separator (rather than a single space) so each
    original text node stays on its own line. This matters a lot for
    precision: a page title like "<h1>Global AI Summit 2026</h1>" sits
    right next to an unrelated "<p>Deadline: March 1, 2026</p>" in the
    DOM, and without a real separator between them a naive fixed
    character window would wrongly associate the title's "Summit" (an
    event keyword) with the neighboring paragraph's date.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    return soup.get_text("\n", strip=True)


def _chunk_spans(text):
    """Split text into small 'clause' chunks on newlines and sentence-
    ending punctuation, returning a list of (start, end) spans.

    This is what keeps keyword <-> date pairing precise: a keyword and a
    date are only associated if they land in the same clause (or, for
    "updated" facts only, one clause apart - see find_facts). This works
    for both HTML-derived text (where "\\n" marks real tag boundaries)
    and raw PDF/plain text (which has no tags, only punctuation).
    """
    spans = []
    start = 0
    for m in re.finditer(r"[.!?\n]+", text):
        end = m.start()
        if end > start:
            spans.append((start, end))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _extract_pdf_text(content):
    """Extract text from a PDF given as bytes, a file path, or a file-like
    object."""
    if PdfReader is None:
        raise RuntimeError("pypdf is required to analyze PDF sources but is not installed.")

    if isinstance(content, (bytes, bytearray)):
        reader = PdfReader(io.BytesIO(content))
    else:
        reader = PdfReader(content)  # path string or file-like object

    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def extract_structured_dates(html):
    """Pull date-relevant fields out of a page's JSON-LD blocks.

    Returns a list of dicts: {"field", "date", "schema_type", "raw"}.
    """
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.find_all("script", attrs={"type": "application/ld+json"})
    date_fields = ["datePublished", "dateModified", "startDate", "endDate", "validThrough"]
    results = []

    for block in blocks:
        raw = block.string or block.get_text()
        if not raw or not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        entities = []
        if isinstance(data, list):
            entities = [e for e in data if isinstance(e, dict)]
        elif isinstance(data, dict):
            if isinstance(data.get("@graph"), list):
                entities = [e for e in data["@graph"] if isinstance(e, dict)]
            else:
                entities = [data]

        for entity in entities:
            schema_type = entity.get("@type", "")
            for field in date_fields:
                if field in entity:
                    parsed = _parse_iso_loose(entity[field])
                    if parsed:
                        results.append({
                            "field": field,
                            "date": parsed,
                            "schema_type": schema_type,
                            "raw": entity[field],
                        })
    return results


def find_facts(text, source_label, source_url):
    """Locate time-sensitive keyword occurrences and pair each with a date
    found in the SAME clause (see _chunk_spans) - not just "nearby" by
    character count, which is what causes cross-paragraph false positives.

    One deliberate exception: for fact_type == "updated" only, if the
    keyword's own clause has no date, the immediately following clause is
    also checked. This covers the common "Last updated:" / "March 1, 2026"
    pattern split across adjacent elements. No other fact type gets this
    fallback, since deadlines/events/hours/prices/availability are almost
    always stated in a single clause and extending the search for them is
    what caused false positives in testing (e.g. a page title matching an
    "event" keyword and picking up an unrelated date from the next line).

    Returns a list of dicts: fact_type, keyword, date, date_confidence,
    snippet, source_label, source_url.
    """
    lowered = text.lower()
    all_dates = extract_dates(text)
    chunks = _chunk_spans(text)
    facts = []

    def chunk_index_for(pos):
        for idx, (s, e) in enumerate(chunks):
            if s <= pos <= e:
                return idx
        return None

    for fact_type, keywords in FACT_KEYWORDS.items():
        for kw in keywords:
            for m in re.finditer(re.escape(kw), lowered):
                kw_start = m.start()
                idx = chunk_index_for(kw_start)
                if idx is None:
                    continue

                window_chunks = [chunks[idx]]
                if fact_type == "updated" and idx + 1 < len(chunks):
                    window_chunks.append(chunks[idx + 1])

                candidates = []
                for (ws, we) in window_chunks:
                    candidates.extend(d for d in all_dates if ws <= d["start"] <= we)
                if not candidates:
                    continue

                nearest = min(candidates, key=lambda d: abs(d["start"] - kw_start))
                win_start = min(c[0] for c in window_chunks)
                win_end = max(c[1] for c in window_chunks)
                snippet = re.sub(r"\s+", " ", text[win_start:win_end]).strip()

                facts.append({
                    "fact_type": fact_type,
                    "keyword": kw,
                    "date": nearest["date"],
                    "date_confidence": nearest["confidence"],
                    "snippet": snippet,
                    "source_label": source_label,
                    "source_url": source_url,
                })

    # Dedupe: multiple keywords often land near the same date (e.g.
    # "deadline" and "submission deadline" both matching one sentence).
    deduped = {}
    for f in facts:
        key = (f["fact_type"], f["date"], f["source_label"])
        deduped.setdefault(key, f)
    return list(deduped.values())


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_expired_deadline(facts, today):
    """FR001: a deadline-type date has passed with no acknowledgement text
    nearby (e.g. 'closed', 'extended to')."""
    findings = []
    for f in facts:
        if f["fact_type"] != "deadline" or f["date"] >= today:
            continue
        if any(ack in f["snippet"].lower() for ack in CLOSED_ACK_WORDS):
            continue

        days_past = (today - f["date"]).days
        severity = "high" if days_past > 14 else "medium"

        findings.append({
            "id": f"FR001-{f['source_label']}-{f['date'].isoformat()}",
            "title": "Expired deadline still presented as active",
            "type": "issue",
            "severity": severity,
            "confidence": f["date_confidence"],
            "evidence": (
                f"On {f['source_label']} ({f['source_url']}), text near "
                f"'{f['keyword']}' references {f['date'].isoformat()}, which is "
                f"{days_past} day(s) in the past, with no visible acknowledgement "
                f"that the deadline has passed. Context: \"{f['snippet']}\""
            ),
            "suggested_action": {
                "summary": (
                    "Update or remove the deadline, or add an explicit note "
                    "(e.g. 'deadline extended to ...' / 'submissions closed') "
                    "so agents and users don't treat it as still open."
                ),
                "priority": "high" if severity == "high" else "medium",
            },
        })
    return findings


def check_expired_event(facts, today):
    """FR002: an event-type date has passed AND the surrounding text still
    uses forward-looking / promotional language."""
    findings = []
    for f in facts:
        if f["fact_type"] != "event" or f["date"] >= today:
            continue
        lowered_snippet = f["snippet"].lower()
        if not any(fl in lowered_snippet for fl in FUTURE_LANGUAGE):
            continue  # a calm past-event recap page - not flagged
        if any(ack in lowered_snippet for ack in CLOSED_ACK_WORDS):
            continue

        days_past = (today - f["date"]).days
        severity = "high" if days_past > 14 else "medium"

        findings.append({
            "id": f"FR002-{f['source_label']}-{f['date'].isoformat()}",
            "title": "Past event still promoted as upcoming",
            "type": "issue",
            "severity": severity,
            "confidence": f["date_confidence"],
            "evidence": (
                f"On {f['source_label']} ({f['source_url']}), the event date "
                f"{f['date'].isoformat()} has passed ({days_past} day(s) ago), but "
                f"the surrounding text still uses forward-looking language near "
                f"'{f['keyword']}'. Context: \"{f['snippet']}\""
            ),
            "suggested_action": {
                "summary": "Update the event date, or move the page to an archive/past-events state.",
                "priority": "high" if severity == "high" else "medium",
            },
        })
    return findings


def check_structured_vs_visible(structured_dates, facts, source_label, source_url):
    """FR003 / FR005: same-page contradictions between JSON-LD dates and
    visible dates for the same fact."""
    findings = []
    visible_event_dates = {f["date"] for f in facts if f["fact_type"] == "event"}
    visible_updated_dates = {f["date"] for f in facts if f["fact_type"] == "updated"}

    for sd in structured_dates:
        if sd["field"] == "startDate" and visible_event_dates and sd["date"] not in visible_event_dates:
            nearest = min(visible_event_dates, key=lambda d: abs((d - sd["date"]).days))
            diff = abs((nearest - sd["date"]).days)
            if diff >= 1:
                findings.append({
                    "id": f"FR003-{source_label}-startDate",
                    "title": "Structured event date conflicts with visible event date",
                    "type": "issue",
                    "severity": "high" if diff > 7 else "medium",
                    "confidence": "high",
                    "evidence": (
                        f"On {source_label} ({source_url}), the JSON-LD 'startDate' is "
                        f"{sd['date'].isoformat()}, but the visible page text states the "
                        f"event date as {nearest.isoformat()} - a {diff}-day discrepancy. "
                        "An AI agent reading structured data vs. reading the visible page "
                        "could report two different dates for the same event."
                    ),
                    "suggested_action": {
                        "summary": "Sync the JSON-LD startDate with the visible event date (or vice versa).",
                        "priority": "high",
                    },
                })

        if sd["field"] == "dateModified" and visible_updated_dates and sd["date"] not in visible_updated_dates:
            nearest = min(visible_updated_dates, key=lambda d: abs((d - sd["date"]).days))
            diff = abs((nearest - sd["date"]).days)
            if diff >= 3:
                findings.append({
                    "id": f"FR005-{source_label}-dateModified",
                    "title": "Structured dateModified disagrees with visible 'last updated' text",
                    "type": "warning",
                    "severity": "medium",
                    "confidence": "high",
                    "evidence": (
                        f"On {source_label} ({source_url}), JSON-LD 'dateModified' is "
                        f"{sd['date'].isoformat()}, but the visible page text says it was "
                        f"updated {nearest.isoformat()} - a {diff}-day gap. Agents trusting "
                        "structured data over visible copy (or vice versa) get an "
                        "inconsistent freshness signal for the same page."
                    ),
                    "suggested_action": {
                        "summary": "Keep dateModified in structured data synced with the visible 'last updated' statement.",
                        "priority": "medium",
                    },
                })
    return findings


def check_cross_resource_conflict(all_facts):
    """FR004: the same time-sensitive fact type (deadline/event) resolves
    to different dates across genuinely different sources. This is the
    ACIFFS-style check and is treated as high severity by design - an
    agent's answer would depend on which resource it happened to fetch."""
    findings = []
    seen_pairs = set()

    for fact_type in ("deadline", "event"):
        by_date = {}
        for f in all_facts:
            if f["fact_type"] == fact_type:
                by_date.setdefault(f["date"], []).append(f)

        distinct_dates = list(by_date.keys())
        if len(distinct_dates) < 2:
            continue

        for i in range(len(distinct_dates)):
            for j in range(i + 1, len(distinct_dates)):
                d1, d2 = distinct_dates[i], distinct_dates[j]
                facts1, facts2 = by_date[d1], by_date[d2]
                sources1 = {f["source_label"] for f in facts1}
                sources2 = {f["source_label"] for f in facts2}

                if sources1 == sources2:
                    continue  # same source(s) only - not a cross-resource conflict

                pair_key = tuple(sorted([d1.isoformat(), d2.isoformat()])) + (fact_type,)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Crude relatedness score: do the two snippets share enough
                # vocabulary to plausibly be describing the same named
                # fact (vs. two unrelated deadlines that happen to both be
                # "deadlines")?
                words1 = set(re.findall(r"[a-z]{5,}", facts1[0]["snippet"].lower()))
                words2 = set(re.findall(r"[a-z]{5,}", facts2[0]["snippet"].lower()))
                overlap = len(words1 & words2) / max(1, len(words1 | words2))
                confidence = "high" if overlap >= 0.15 else "medium"

                evidence = (
                    f"'{fact_type}' is reported as {d1.isoformat()} in "
                    f"{', '.join(sorted(sources1))} (e.g. \"{facts1[0]['snippet']}\") but as "
                    f"{d2.isoformat()} in {', '.join(sorted(sources2))} "
                    f"(e.g. \"{facts2[0]['snippet']}\"). An AI agent retrieving different "
                    "resources for this fact could surface either date."
                )
                if confidence == "medium":
                    evidence += (
                        " (Note: these snippets share limited vocabulary overlap - verify "
                        "they refer to the same named deadline/event before treating this "
                        "as a confirmed contradiction.)"
                    )

                findings.append({
                    "id": f"FR004-{fact_type}-{d1.isoformat()}-{d2.isoformat()}",
                    "title": f"Cross-resource conflict: {fact_type} date differs between sources",
                    "type": "issue",
                    "severity": "high",
                    "confidence": confidence,
                    "evidence": evidence,
                    "suggested_action": {
                        "summary": (
                            f"Confirm which {fact_type} date is authoritative and correct "
                            "the other source(s) to match."
                        ),
                        "priority": "high",
                    },
                })
    return findings


def check_stale_time_sensitive_statement(facts, today):
    """FR006: hours/price/availability text that is EXPLICITLY self-dated
    ('as of ...' / 'updated ...') and that date is old. Never fires from
    page age alone - only from a date the page itself attached."""
    findings = []
    for f in facts:
        if f["fact_type"] not in ("hours", "price", "availability"):
            continue
        lowered = f["snippet"].lower()
        if "as of" not in lowered and "updated" not in lowered:
            continue  # no explicit self-declared freshness claim - skip

        days_old = (today - f["date"]).days
        if days_old < STALE_THRESHOLD_DAYS:
            continue

        findings.append({
            "id": f"FR006-{f['source_label']}-{f['fact_type']}-{f['date'].isoformat()}",
            "title": f"Self-declared '{f['fact_type']}' date is stale",
            "type": "opportunity",
            "severity": "low" if days_old < 365 else "medium",
            "confidence": "medium",
            "evidence": (
                f"On {f['source_label']} ({f['source_url']}), text near '{f['keyword']}' "
                f"is explicitly dated {f['date'].isoformat()} ({days_old} days ago). "
                f"Context: \"{f['snippet']}\""
            ),
            "suggested_action": {
                "summary": (
                    f"Verify current {f['fact_type']} and refresh the stated date - this "
                    "page explicitly claims a freshness date that is old."
                ),
                "priority": "low" if days_old < 365 else "medium",
            },
        })
    return findings


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


def audit_freshness(sources, today=None):
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
        if structured_dates:
            findings.extend(check_structured_vs_visible(structured_dates, facts, label, url))

    findings.extend(check_cross_resource_conflict(all_facts))
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