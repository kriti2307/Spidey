"""
Freshness / Information-Staleness detector - extraction layer.

Part of the AI-discoverability audit toolkit freshness skill. This module owns everything that turns raw HTML/PDF/text into structured facts a check can reason about:

  - date parsing from free text (extract_dates) and ISO/structured-data
    values (_parse_iso_loose)
  - visible-text extraction with script/style/JSON-LD stripped out
    (_get_visible_text)
  - time-sensitive keyword <-> date pairing, scoped to a single clause so
    unrelated text doesn't get associated (find_facts)
  - JSON-LD date field extraction (extract_structured_dates)
  - PDF text extraction (_extract_pdf_text)
  - copyright-year extraction (extract_copyright_year)
  - snapshot computation for change-over-time detection (compute_snapshot
    and its helpers) - see freshness_checks.py's module docstring for why
    snapshot-based diffing exists and how it's used

It does NOT contain any FRxxx check logic or severity/evidence
construction - see freshness_checks.py for that. It does NOT orchestrate
a full audit run - see audit_freshness.py for that.

No dependencies beyond the project's existing requests / BeautifulSoup /
pypdf.
"""

import hashlib
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

COPYRIGHT_PATTERN = re.compile(r'(?:©|\(c\)|copyright)\s*(\d{4})(?:\s*[-–]\s*(\d{4}))?', re.IGNORECASE)


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


def extract_copyright_year(text):
    """Return the latest year found in a '© YYYY' / '© YYYY-YYYY' /
    'Copyright YYYY' style statement, or None if none found."""
    years = []
    for m in COPYRIGHT_PATTERN.finditer(text):
        years.append(int(m.group(1)))
        if m.group(2):
            years.append(int(m.group(2)))
    return max(years) if years else None


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

# Text suggesting an offer/product is still being presented as purchasable -
# used by check_expired_offer to decide whether an expired validThrough is
# still being contradicted by the visible page (vs. a page that already
# shows it as out of stock/expired, which is not a defect).
STILL_AVAILABLE_LANGUAGE = [
    "add to cart", "buy now", "in stock", "available now", "book now",
]

STALE_THRESHOLD_DAYS = 180  # for FR006 (self-declared "as of" staleness)
RECENT_UPDATE_THRESHOLD_DAYS = 14  # for FR007 (fake-freshness signal)
COPYRIGHT_STALE_THRESHOLD_DAYS = 365  # for FR011
LASTMOD_UNIFORMITY_THRESHOLD = 0.7  # fraction of sitemap sharing one date, for FR008

# Snapshot-diffing thresholds (FR013-FR015). Since snapshots store a text
# length rather than the full historical text (see compute_snapshot's
# docstring for why), "significant change" is approximated by relative +
# absolute character-count delta rather than a true text diff ratio.
SNAPSHOT_SIZE_CHANGE_RATIO = 0.03   # 3% length change
SNAPSHOT_SIZE_CHANGE_MIN_CHARS = 50  # ...and at least this many characters,
                                      # so short pages don't trip on noise


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

            # availability is a sibling signal to validThrough, not a date
            # itself - captured here so check_expired_offer doesn't need
            # to re-walk the JSON-LD structure separately.
            if "validThrough" in entity:
                availability = str(entity.get("availability", ""))
                results.append({
                    "field": "_availability_context",
                    "date": None,
                    "schema_type": schema_type,
                    "raw": availability,
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


def _normalize_for_hash(text):
    """Collapse whitespace only - do NOT lowercase or strip punctuation.
    The hash needs to catch genuine wording/number changes, not just
    reformat them away; whitespace is the only thing safe to normalize
    without risking masking a real edit."""
    return re.sub(r"\s+", " ", text or "").strip()


def compute_content_hash(text):
    return hashlib.sha256(_normalize_for_hash(text).encode("utf-8")).hexdigest()


def extract_metadata_signature(html):
    """Small, storable fingerprint of the page's metadata layer (title,
    meta description, canonical URL, and the structured-data
    dateModified/datePublished values) - the fields a purely cosmetic /
    SEO-only edit is most likely to touch without changing the actual
    content."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()

    canonical = ""
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    if canonical_tag and canonical_tag.get("href"):
        canonical = canonical_tag["href"].strip()

    structured_dates = extract_structured_dates(html)
    date_modified = next((sd["date"] for sd in structured_dates if sd["field"] == "dateModified" and sd["date"]), None)
    date_published = next((sd["date"] for sd in structured_dates if sd["field"] == "datePublished" and sd["date"]), None)

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "dateModified": date_modified.isoformat() if date_modified else None,
        "datePublished": date_published.isoformat() if date_published else None,
    }


def compute_snapshot(html, url, today=None):
    """Compute a storable snapshot for one HTML page.

    Returns:
        {
          "url": str,
          "captured_at": "YYYY-MM-DD",
          "text_hash": sha256 hex digest of normalized visible text,
          "text_length": int,
          "metadata": {title, description, canonical, dateModified, datePublished},
          "metadata_hash": sha256 hex digest of the metadata dict,
        }

    Deliberately does NOT store the full page text. Two reasons: (1) it
    keeps snapshots cheap to persist across many URLs over time, and (2)
    it avoids the entrypoint having to retain a growing archive of full
    page contents just to run a freshness check. The trade-off is that
    "how much changed" is approximated via text_length delta rather than
    a true diff - see check_unsignaled_content_change for how that
    approximation is used and its stated confidence level.
    """
    if today is None:
        today = date.today()
    visible_text = _get_visible_text(html)
    metadata = extract_metadata_signature(html)
    return {
        "url": url,
        "captured_at": today.isoformat(),
        "text_hash": compute_content_hash(visible_text),
        "text_length": len(_normalize_for_hash(visible_text)),
        "metadata": metadata,
        "metadata_hash": hashlib.sha256(json.dumps(metadata, sort_keys=True).encode("utf-8")).hexdigest(),
    }