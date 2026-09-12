# Example findings (illustrative)

These examples show the expected output format, severity/confidence
calibration, and the elements every finding must include: specific
evidence, mechanism-sound fixes, and explicit inference-vs-proof framing
where a check is inferred rather than directly evidenced. They are format
references, not the basis for the checks themselves - the checks are
derived from the reasoning in `references/freshness-checklist.md` and are
designed to generalize to any site.

## FR001 — Expired deadline still presented as active

```json
{
  "id": "FR001-Homepage-2026-03-01",
  "type": "issue",
  "title": "Expired deadline still presented as active",
  "severity": "high",
  "confidence": "high",
  "evidence": "On Homepage (https://example.com), text near 'submission deadline' references 2026-03-01, which is 22 day(s) in the past, with no visible acknowledgement that the deadline has passed. Context: \"Submission deadline: March 1, 2026\"",
  "suggested_action": {
    "summary": "Update or remove the deadline, or add an explicit note (e.g. 'deadline extended to ...' / 'submissions closed') so agents and users don't treat it as still open.",
    "priority": "high"
  }
}
```

## FR002 — Past event still promoted as upcoming

```json
{
  "id": "FR002-Homepage-2026-03-15",
  "type": "issue",
  "title": "Past event still promoted as upcoming",
  "severity": "medium",
  "confidence": "high",
  "evidence": "On Homepage (https://example.com), the event date 2026-03-15 has passed (8 day(s) ago), but the surrounding text still uses forward-looking language near 'will be held'. Context: \"The conference will be held on March 15, 2026 - join us!\"",
  "suggested_action": {
    "summary": "Update the event date, or move the page to an archive/past-events state.",
    "priority": "medium"
  }
}
```

## FR004 — Cross-resource conflict (ACIFFS case)

```json
{
  "id": "FR004-deadline-2026-01-15-2026-01-30",
  "type": "issue",
  "title": "Cross-resource conflict: deadline date differs between sources",
  "severity": "high",
  "confidence": "high",
  "evidence": "'deadline' is reported as 2026-01-15 in Homepage (e.g. \"Abstract submission deadline: January 15, 2026\") but as 2026-01-30 in Brochure PDF (e.g. \"Abstract submission deadline: January 30, 2026\"). An AI agent retrieving different resources for this fact could surface either date.",
  "suggested_action": {
    "summary": "Confirm which deadline date is authoritative and correct the other source(s) to match.",
    "priority": "high"
  }
}
```

## FR003 — Structured startDate conflicts with visible event date

```json
{
  "id": "FR003-Homepage-startDate",
  "type": "issue",
  "title": "Structured event date conflicts with visible event date",
  "severity": "high",
  "confidence": "high",
  "evidence": "On Homepage (https://example.com), the JSON-LD 'startDate' is 2026-01-10, but the visible page text states the event date as 2026-01-17 - a 7-day discrepancy. An AI agent reading structured data vs. reading the visible page could report two different dates for the same event.",
  "suggested_action": {
    "summary": "Sync the JSON-LD startDate with the visible event date (or vice versa).",
    "priority": "high"
  }
}
```

## FR007 — Fake-freshness signal (inferred, no snapshot available)

```json
{
  "id": "FR007-Homepage-deadline-2026-03-01",
  "type": "issue",
  "title": "Page claims a recent update but still contains an unresolved stale fact",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "On Homepage (https://example.com), structured 'dateModified' claims the page was updated 2026-09-05 (within the last 14 days), but it still contains an unresolved stale deadline from 2026-03-01: \"Submission deadline: March 1, 2026\". This pattern (date bumped, substance unchanged) is what search/AI systems specifically treat as a manipulated freshness signal, distinct from the underlying staleness itself.",
  "suggested_action": {
    "summary": "Either the dateModified value is inaccurate (revert it), or the flagged fact was missed during the update (fix it) - don't leave both as-is, since the mismatch itself damages trust in this page's freshness signals going forward.",
    "priority": "medium"
  }
}
```

## FR010 — Expired Offer.validThrough still shown as available

```json
{
  "id": "FR010-ProductPage-2026-08-15",
  "type": "issue",
  "title": "Offer validThrough has expired but item still presented as available",
  "severity": "medium",
  "confidence": "high",
  "evidence": "On ProductPage (https://example.com/deals/summer-sale), the structured-data Offer's 'validThrough' is 2026-08-15, which is 28 day(s) in the past, but the page's availability field and/or visible text (e.g. purchase call-to-action language) still presents the item as available.",
  "suggested_action": {
    "summary": "Update validThrough to the correct current date, or set availability to OutOfStock/Discontinued if the offer has genuinely ended.",
    "priority": "medium"
  }
}
```

## FR011 — Stale footer copyright year

```json
{
  "id": "FR011-Homepage-2019",
  "type": "opportunity",
  "title": "Footer copyright year appears outdated",
  "severity": "low",
  "confidence": "low",
  "evidence": "On Homepage (https://example.com), the copyright statement shows 2019, 7 year(s) behind the current year. On its own this is a weak signal (easy to forget, not tied to actual content changes), but it's a commonly used quick heuristic for site maintenance and worth a low-cost fix.",
  "suggested_action": {
    "summary": "Update the footer copyright year, or make it dynamic (current year).",
    "priority": "low"
  }
}
```

## FR008 — Suspiciously uniform sitemap lastmod

```json
{
  "id": "FR008-sitemap-uniform-2026-09-01",
  "type": "warning",
  "title": "Sitemap lastmod values are suspiciously uniform",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "47 of 52 sitemap URLs (90%) share the identical lastmod value 2026-09-01. This is the typical fingerprint of a mass/automated timestamp bump rather than genuine per-page content changes, and is the specific pattern that leads search engines to stop trusting a site's lastmod values altogether.",
  "suggested_action": {
    "summary": "Only update lastmod for URLs whose substantive content, structured data, or important links actually changed on that date - not on every site-wide deploy or CMS re-save.",
    "priority": "medium"
  }
}
```

## FR013 — dateModified advanced with zero text change (proven, requires snapshot)

```json
{
  "id": "FR013-Homepage-2026-09-10",
  "type": "issue",
  "title": "dateModified advanced with zero underlying text change",
  "severity": "high",
  "confidence": "high",
  "evidence": "On Homepage (https://example.com), structured 'dateModified' changed from 2026-08-01 to 2026-09-10 between snapshots taken 2026-08-01 and 2026-09-12, but the page's visible text is byte-for-byte identical (matching content hash) across both snapshots. This is direct evidence the update was a date-only bump, not a real content change.",
  "suggested_action": {
    "summary": "Only advance dateModified when the page's actual content, structured data, or important links change - not on unrelated deploys, template touches, or scheduled re-saves.",
    "priority": "high"
  }
}
```

## FR015 — Substantial content change, no freshness signal moved (requires snapshot)

```json
{
  "id": "FR015-ProductPage-2026-09-12",
  "type": "warning",
  "title": "Substantial content change not reflected in any freshness signal",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "On ProductPage (https://example.com/widget), the visible text changed substantially between the snapshot on 2026-08-01 and 2026-09-12 (content length changed by 340 characters, 18%), but 'dateModified' did not change (still 2026-06-01). Crawlers/agents that rely on dateModified to decide whether to re-fetch this page may not notice the update happened.",
  "suggested_action": {
    "summary": "Update dateModified (and sitemap lastmod, if applicable) whenever a substantive content edit ships.",
    "priority": "medium"
  }
}
```