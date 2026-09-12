"""
Freshness / Information-Staleness detector - checks layer.

Part of the AI-discoverability audit toolkitcfreshness skill. This module contains every FRxxx check function - each takes already-extracted facts/dates/snapshots (see
freshness_extraction.py) and returns a list of finding dicts: id, title,
type, severity, confidence, evidence, suggested_action {summary, priority}.

It intentionally does NOT do structured-data auditing, crawlability,
entity/reputation checks, or non-text auditing - those are separate
skills in the marketplace.

------------------------------------------------------------------------
WHY THESE CHECKS LOOK THE WAY THEY DO
------------------------------------------------------------------------
"Old" != "stale". A five-year-old About Us page is fine. A five-day-past
"Early bird deadline: March 1" statement that's still live on March 15 is
a real problem for anything (human or AI agent) making a decision from it.

So instead of asking "how old is this page/date", every check here asks
one of a few sharper questions:

  1. Is this specific fact TIME-SENSITIVE (a deadline, an event date, a
     price, hours, availability) AND does the page's own language suggest
     it has already lapsed while still being presented as live?

  2. Do independent sources an AI agent might retrieve for the SAME fact
     (this page, another page, a linked PDF, the page's own structured
     data) DISAGREE with each other?

  3. Does the page's OWN freshness claim (a recent dateModified / sitemap
     lastmod) actually hold up - or does the page still contain a stale
     fact it never touched? Per Google's own guidance, a date bump with no
     substantive change ("fake freshness") is a distinct, detectable
     failure mode from staleness itself - and once a source is caught
     doing this, freshness signals from it are trusted less broadly, not
     just for the one date.

  4. Do crawl-freshness-adjacent signals (sitemap lastmod) look
     technically implausible - a future date, or the exact same lastmod
     mass-applied across many URLs regardless of whether they actually
     changed - which is itself a documented manipulation pattern rather
     than a place a specific fact is wrong.

  5. Has the page's ACTUAL content changed since a previous snapshot at
     all - independent of what any date field claims? A dateModified
     bump proves nothing on its own; a content hash comparison against a
     prior snapshot does. This lets these checks catch both directions of
     the same underlying problem: a freshness signal that changed with no
     real content behind it (direct proof of "fake freshness", stronger
     than FR007's text-inference version of the same idea), and the
     inverse - real content changed but no freshness signal reflects it,
     which is just as bad for a crawler deciding whether to re-fetch.

(2) and (3) are weighted as more interesting than plain staleness - a
single old date is a maybe; two live sources disagreeing about the same
fact, or a page claiming to be freshly updated while still visibly wrong,
are real integrity problems regardless of how old any one date is. This
mirrors the ACIFFS case: webpage vs. PDF brochure vs. another official
page each gave a different conference/deadline date.
------------------------------------------------------------------------
"""

import re
from datetime import date

from freshness_extraction import (
    extract_copyright_year,
    _parse_iso_loose,
    CLOSED_ACK_WORDS,
    FUTURE_LANGUAGE,
    STILL_AVAILABLE_LANGUAGE,
    STALE_THRESHOLD_DAYS,
    RECENT_UPDATE_THRESHOLD_DAYS,
    COPYRIGHT_STALE_THRESHOLD_DAYS,
    LASTMOD_UNIFORMITY_THRESHOLD,
    SNAPSHOT_SIZE_CHANGE_RATIO,
    SNAPSHOT_SIZE_CHANGE_MIN_CHARS,
)


# ---------------------------------------------------------------------------
# Checks - facts vs. today
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
# Checks - structured data vs. visible content (same page)
# ---------------------------------------------------------------------------

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


def check_expired_offer(structured_dates, facts, source_label, source_url, today):
    """FR010: Schema.org Offer.validThrough has passed, but the page still
    presents the item as purchasable/available (either via visible
    "add to cart"/"in stock"-style language, or an availability field that
    isn't an OutOfStock/Discontinued value).

    This is a commerce-specific, schema-native staleness check: unlike
    text-derived dates, validThrough is a structured field explicitly
    designed to bound an offer's validity, so an expired value is a
    high-confidence, unambiguous signal rather than a heuristic guess.
    """
    findings = []
    valid_through_entries = [sd for sd in structured_dates if sd["field"] == "validThrough"]
    availability_entries = [sd for sd in structured_dates if sd["field"] == "_availability_context"]

    if not valid_through_entries:
        return findings

    still_available_text = any(
        phrase in f["snippet"].lower()
        for f in facts
        for phrase in STILL_AVAILABLE_LANGUAGE
    )
    stale_availability_field = any(
        "outofstock" not in a["raw"].lower() and "discontinued" not in a["raw"].lower()
        for a in availability_entries
    ) if availability_entries else True  # no availability field at all = can't rule it out

    for sd in valid_through_entries:
        if sd["date"] >= today:
            continue
        if not (still_available_text or stale_availability_field):
            continue  # page already reflects the offer as no longer available

        days_past = (today - sd["date"]).days
        findings.append({
            "id": f"FR010-{source_label}-{sd['date'].isoformat()}",
            "title": "Offer validThrough has expired but item still presented as available",
            "type": "issue",
            "severity": "high" if days_past > 14 else "medium",
            "confidence": "high",
            "evidence": (
                f"On {source_label} ({source_url}), the structured-data Offer's "
                f"'validThrough' is {sd['date'].isoformat()}, which is {days_past} day(s) "
                "in the past, but the page's availability field and/or visible text "
                "(e.g. purchase call-to-action language) still presents the item as "
                "available."
            ),
            "suggested_action": {
                "summary": (
                    "Update validThrough to the correct current date, or set availability "
                    "to OutOfStock/Discontinued if the offer has genuinely ended."
                ),
                "priority": "high" if days_past > 14 else "medium",
            },
        })
    return findings


def check_fake_freshness_signal(structured_dates, facts, source_label, source_url, today):
    """FR007: the page's own freshness claim (a recent dateModified) is
    contradicted by a stale fact still sitting unresolved on the same
    page. This targets the specific failure mode Google has explicitly
    called out as distinct from ordinary staleness: a date bump with no
    substantive change. It is a stronger, more specific signal than "this
    page is old" - it's "this page claims to have just been fixed, and
    demonstrably wasn't."
    """
    findings = []
    recent_mods = [
        sd for sd in structured_dates
        if sd["field"] == "dateModified"
        and sd["date"] is not None
        and 0 <= (today - sd["date"]).days <= RECENT_UPDATE_THRESHOLD_DAYS
    ]
    if not recent_mods:
        return findings

    unresolved_stale_facts = []
    for f in facts:
        if f["fact_type"] == "deadline" and f["date"] < today:
            if not any(ack in f["snippet"].lower() for ack in CLOSED_ACK_WORDS):
                unresolved_stale_facts.append(f)
        elif f["fact_type"] == "event" and f["date"] < today:
            lowered = f["snippet"].lower()
            if any(fl in lowered for fl in FUTURE_LANGUAGE) and not any(ack in lowered for ack in CLOSED_ACK_WORDS):
                unresolved_stale_facts.append(f)

    if not unresolved_stale_facts:
        return findings

    most_recent_mod = max(recent_mods, key=lambda sd: sd["date"])
    for f in unresolved_stale_facts:
        findings.append({
            "id": f"FR007-{source_label}-{f['fact_type']}-{f['date'].isoformat()}",
            "title": "Page claims a recent update but still contains an unresolved stale fact",
            "type": "issue",
            "severity": "medium",
            "confidence": "medium",
            "evidence": (
                f"On {source_label} ({source_url}), structured 'dateModified' claims the "
                f"page was updated {most_recent_mod['date'].isoformat()} (within the last "
                f"{RECENT_UPDATE_THRESHOLD_DAYS} days), but it still contains an unresolved "
                f"stale {f['fact_type']} from {f['date'].isoformat()}: \"{f['snippet']}\". "
                "This pattern (date bumped, substance unchanged) is what search/AI systems "
                "specifically treat as a manipulated freshness signal, distinct from the "
                "underlying staleness itself."
            ),
            "suggested_action": {
                "summary": (
                    "Either the dateModified value is inaccurate (revert it), or the "
                    "flagged fact was missed during the update (fix it) - don't leave both "
                    "as-is, since the mismatch itself damages trust in this page's freshness "
                    "signals going forward."
                ),
                "priority": "medium",
            },
        })
    return findings


def check_stale_copyright(text, source_label, source_url, today):
    """FR011: a footer-style copyright year that is significantly behind
    the current year. Low-confidence, low-severity on its own (copyright
    years are routinely forgotten even on well-maintained sites), but
    cheap to check and a real signal casual visitors and quick heuristics
    both use as a first-glance staleness tell."""
    findings = []
    year = extract_copyright_year(text)
    if year is None:
        return findings

    days_stale = (today - date(year, 1, 1)).days
    if days_stale < COPYRIGHT_STALE_THRESHOLD_DAYS:
        return findings

    years_behind = today.year - year
    findings.append({
        "id": f"FR011-{source_label}-{year}",
        "title": "Footer copyright year appears outdated",
        "type": "opportunity",
        "severity": "low",
        "confidence": "low",
        "evidence": (
            f"On {source_label} ({source_url}), the copyright statement shows {year}, "
            f"{years_behind} year(s) behind the current year. On its own this is a weak "
            "signal (easy to forget, not tied to actual content changes), but it's a "
            "commonly used quick heuristic for site maintenance and worth a low-cost fix."
        ),
        "suggested_action": {
            "summary": "Update the footer copyright year, or make it dynamic (current year).",
            "priority": "low",
        },
    })
    return findings


# ---------------------------------------------------------------------------
# Checks - cross-resource (multiple pages / PDF / sitemap)
# ---------------------------------------------------------------------------

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


def check_sitemap_signals(sitemap_entries, today):
    """FR008 / FR009: sitemap <lastmod> plausibility checks.

    FR009 (future lastmod): a lastmod date after today is a flat data-
    quality bug - the crawl-freshness signal is unusable as given.

    FR008 (mass-uniform lastmod): per Google/Bing guidance, lastmod is
    meant to reflect real, per-URL content changes. If a large share of
    sitemap entries share the exact same lastmod value, that's the
    fingerprint of an automated mass "touch" (e.g. every page re-saved by
    a CMS migration or a deliberate freshness-signal manipulation) rather
    than genuine per-page updates - the documented reason Google says it
    stops trusting a site's lastmod values once caught doing this.

    sitemap_entries: list of dicts, each {"url": str, "lastmod": str}
    (lastmod as an ISO date/datetime string, per the sitemap spec).
    """
    findings = []
    if not sitemap_entries:
        return findings

    parsed = []
    for entry in sitemap_entries:
        d = _parse_iso_loose(entry.get("lastmod", ""))
        if d:
            parsed.append({"url": entry.get("url", ""), "date": d})

    if not parsed:
        return findings

    future_entries = [p for p in parsed if p["date"] > today]
    if future_entries:
        sample_urls = ", ".join(p["url"] for p in future_entries[:3])
        findings.append({
            "id": "FR009-sitemap-future",
            "title": "Sitemap lastmod date(s) are in the future",
            "type": "issue",
            "severity": "medium",
            "confidence": "high",
            "evidence": (
                f"{len(future_entries)} sitemap URL(s) have a <lastmod> date after today, "
                f"e.g.: {sample_urls}. A future lastmod is not a meaningful freshness "
                "signal and typically indicates a clock, timezone, or generation bug."
            ),
            "suggested_action": {
                "summary": "Fix the sitemap generation logic so lastmod never exceeds the current date.",
                "priority": "medium",
            },
        })

    date_counts = {}
    for p in parsed:
        date_counts.setdefault(p["date"], []).append(p["url"])

    most_common_date, urls_with_date = max(date_counts.items(), key=lambda kv: len(kv[1]))
    fraction = len(urls_with_date) / len(parsed)

    if len(parsed) >= 10 and fraction >= LASTMOD_UNIFORMITY_THRESHOLD:
        findings.append({
            "id": f"FR008-sitemap-uniform-{most_common_date.isoformat()}",
            "title": "Sitemap lastmod values are suspiciously uniform",
            "type": "warning",
            "severity": "medium",
            "confidence": "medium",
            "evidence": (
                f"{len(urls_with_date)} of {len(parsed)} sitemap URLs "
                f"({fraction:.0%}) share the identical lastmod value "
                f"{most_common_date.isoformat()}. This is the typical fingerprint of a "
                "mass/automated timestamp bump rather than genuine per-page content "
                "changes, and is the specific pattern that leads search engines to "
                "stop trusting a site's lastmod values altogether."
            ),
            "suggested_action": {
                "summary": (
                    "Only update lastmod for URLs whose substantive content, structured "
                    "data, or important links actually changed on that date - not on every "
                    "site-wide deploy or CMS re-save."
                ),
                "priority": "medium",
            },
        })

    return findings


def check_sitemap_vs_page_freshness(sitemap_entries, structured_dates, facts, source_label, source_url, today):
    """FR012: for a page whose URL also appears in the sitemap, check
    whether the sitemap's claimed lastmod roughly agrees with the page's
    own freshness signals (structured dateModified, or a visible "last
    updated" statement). A large gap either way means at least one of
    these signals is wrong - and a downstream system has no way to know
    which to trust."""
    findings = []
    if not sitemap_entries:
        return findings

    matching_entry = next((e for e in sitemap_entries if e.get("url") == source_url), None)
    if not matching_entry:
        return findings

    sitemap_date = _parse_iso_loose(matching_entry.get("lastmod", ""))
    if not sitemap_date:
        return findings

    page_dates = [sd["date"] for sd in structured_dates if sd["field"] == "dateModified" and sd["date"]]
    page_dates += [f["date"] for f in facts if f["fact_type"] == "updated"]
    if not page_dates:
        return findings

    nearest_page_date = min(page_dates, key=lambda d: abs((d - sitemap_date).days))
    diff = abs((nearest_page_date - sitemap_date).days)
    if diff < 30:
        return findings

    findings.append({
        "id": f"FR012-{source_label}",
        "title": "Sitemap lastmod disagrees with the page's own freshness signal",
        "type": "warning",
        "severity": "low" if diff < 90 else "medium",
        "confidence": "medium",
        "evidence": (
            f"The sitemap lists {source_url} with lastmod {sitemap_date.isoformat()}, but "
            f"the page's own dateModified/'last updated' text says {nearest_page_date.isoformat()} "
            f"- a {diff}-day gap. At least one of these two freshness signals does not "
            "reflect reality."
        ),
        "suggested_action": {
            "summary": "Ensure the sitemap generator and the page's own update timestamp read from the same source of truth.",
            "priority": "low" if diff < 90 else "medium",
        },
    })
    return findings


def check_no_real_change_since_freshness_claim(previous_snapshot, current_snapshot, source_label, source_url):
    """FR013: dateModified advanced between the previous and current
    snapshot, but the page's text hash is identical. This is direct,
    unambiguous proof of the "fake freshness" pattern - stronger evidence
    than FR007, which only infers it from an unresolved stale fact still
    being present. Here we know for certain nothing in the visible text
    changed at all."""
    if not previous_snapshot:
        return []

    prev_dm = previous_snapshot.get("metadata", {}).get("dateModified")
    curr_dm = current_snapshot.get("metadata", {}).get("dateModified")

    if not prev_dm or not curr_dm or prev_dm == curr_dm:
        return []
    if current_snapshot["text_hash"] != previous_snapshot["text_hash"]:
        return []  # text did change - not this failure mode

    return [{
        "id": f"FR013-{source_label}-{curr_dm}",
        "title": "dateModified advanced with zero underlying text change",
        "type": "issue",
        "severity": "high",
        "confidence": "high",
        "evidence": (
            f"On {source_label} ({source_url}), structured 'dateModified' changed from "
            f"{prev_dm} to {curr_dm} between snapshots taken {previous_snapshot['captured_at']} "
            f"and {current_snapshot['captured_at']}, but the page's visible text is "
            "byte-for-byte identical (matching content hash) across both snapshots. This is "
            "direct evidence the update was a date-only bump, not a real content change."
        ),
        "suggested_action": {
            "summary": (
                "Only advance dateModified when the page's actual content, structured "
                "data, or important links change - not on unrelated deploys, template "
                "touches, or scheduled re-saves."
            ),
            "priority": "high",
        },
    }]


def check_metadata_only_change(previous_snapshot, current_snapshot, source_label, source_url):
    """FR014: metadata (title/description/canonical) changed between
    snapshots but the visible text hash did not. Broader and lower-
    severity than FR013 - this doesn't require a dateModified claim at
    all, just flags that the only detectable change was in the
    SEO/metadata layer, which is worth surfacing distinctly since it
    often indicates a cosmetic tweak rather than a substantive update."""
    if not previous_snapshot:
        return []
    if current_snapshot["text_hash"] != previous_snapshot["text_hash"]:
        return []
    if current_snapshot["metadata_hash"] == previous_snapshot["metadata_hash"]:
        return []

    changed_fields = [
        key for key in ("title", "description", "canonical")
        if previous_snapshot.get("metadata", {}).get(key) != current_snapshot.get("metadata", {}).get(key)
    ]
    if not changed_fields:
        return []  # only the date fields changed - that's FR013's concern, not this one

    return [{
        "id": f"FR014-{source_label}-{current_snapshot['captured_at']}",
        "title": "Metadata changed with no underlying text change",
        "type": "warning",
        "severity": "low",
        "confidence": "medium",
        "evidence": (
            f"On {source_label} ({source_url}), the following metadata field(s) changed "
            f"since the snapshot on {previous_snapshot['captured_at']}: {', '.join(changed_fields)}. "
            "The page's visible text is otherwise unchanged (matching content hash), "
            "suggesting a metadata/SEO-only edit rather than a substantive content update."
        ),
        "suggested_action": {
            "summary": (
                "No action required if this was an intentional metadata-only edit; "
                "verify it wasn't meant to accompany a content update that didn't ship."
            ),
            "priority": "low",
        },
    }]


def check_unsignaled_content_change(previous_snapshot, current_snapshot, source_label, source_url):
    """FR015: the inverse failure mode - real content changed (text hash
    differs, by more than a noise-level length delta) but no freshness
    signal (dateModified) advanced to reflect it. This matters because a
    crawler/agent deciding whether to re-fetch a page relies on exactly
    that signal; a real change with a stale dateModified means the new
    content may simply never get picked up."""
    if not previous_snapshot:
        return []
    if current_snapshot["text_hash"] == previous_snapshot["text_hash"]:
        return []  # no change at all - nothing to signal

    prev_len = previous_snapshot.get("text_length", 0)
    curr_len = current_snapshot.get("text_length", 0)
    abs_delta = abs(curr_len - prev_len)
    ratio_delta = abs_delta / max(prev_len, 1)

    if abs_delta < SNAPSHOT_SIZE_CHANGE_MIN_CHARS or ratio_delta < SNAPSHOT_SIZE_CHANGE_RATIO:
        return []  # change detected but small enough it may be minor copy edits

    prev_dm = previous_snapshot.get("metadata", {}).get("dateModified")
    curr_dm = current_snapshot.get("metadata", {}).get("dateModified")
    if prev_dm != curr_dm:
        return []  # freshness signal DID move - this is the healthy case, not a finding

    return [{
        "id": f"FR015-{source_label}-{current_snapshot['captured_at']}",
        "title": "Substantial content change not reflected in any freshness signal",
        "type": "warning",
        "severity": "medium",
        "confidence": "medium",
        "evidence": (
            f"On {source_label} ({source_url}), the visible text changed substantially "
            f"between the snapshot on {previous_snapshot['captured_at']} and "
            f"{current_snapshot['captured_at']} (content length changed by {abs_delta} "
            f"characters, {ratio_delta:.0%}), but 'dateModified' did not change "
            f"(still {curr_dm or 'unset'}). Crawlers/agents that rely on dateModified to "
            "decide whether to re-fetch this page may not notice the update happened."
        ),
        "suggested_action": {
            "summary": "Update dateModified (and sitemap lastmod, if applicable) whenever a substantive content edit ships.",
            "priority": "medium",
        },
    }]