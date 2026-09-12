# Freshness / Corroboration Audit — Detailed Checklist

This file contains the exhaustive detection logic behind each check in
`SKILL.md`. Use this when a judgment call needs more detail than the
high-level procedure provides. `SKILL.md` stays lean; this file holds the
depth.

Core framing: "old" is not "stale." A check only fires when there's a
specific, time-sensitive claim that plausibly no longer holds, or when two
sources/signals disagree about the same fact - never from page age alone.

---

## FACTS VS. TODAY

### FR001 — Expired deadline still presented as active
- [ ] Locate deadline-type keyword phrases ("submission deadline",
      "register by", "closes on", etc.) paired with a date in the same
      clause (see `find_facts` in the extraction layer for the
      clause-pairing logic - this is what avoids cross-paragraph false
      associations).
- [ ] Skip if the date is today or future.
- [ ] Skip if the surrounding text already acknowledges the deadline has
      passed ("deadline has passed", "submissions closed", "extended
      to...").
- [ ] Flag otherwise.
- **Severity:** high if >14 days past, else medium.

### FR002 — Past event still promoted as upcoming
- [ ] Locate event-type keyword phrases ("will be held", "scheduled
      for", etc.) paired with a past date.
- [ ] Only flag if the surrounding text ALSO uses forward-looking /
      promotional language ("join us", "register now", "save the date").
      A calm past-event recap page mentioning a past date is not flagged
      - this is the key false-positive guard, since plenty of legitimate
      pages describe events that already happened.
- [ ] Skip if already acknowledged as closed/past.
- **Severity:** high if >14 days past, else medium.

### FR006 — Self-declared stale hours/price/availability
- [ ] Only applies to hours/price/availability facts that are explicitly
      self-dated ("as of...", "updated..."). Never fires from page age
      alone - only from a date the page itself attached to this specific
      claim.
- [ ] Flag if that self-declared date is ≥180 days old.
- **Severity:** low under 365 days old, medium beyond that. Framed as
  `type: opportunity` rather than a hard issue, since the underlying fact
  might still be accurate - the page just hasn't re-confirmed it.

---

## SAME-PAGE CONSISTENCY

### FR003 — Structured `startDate` vs. visible event date
- [ ] Compare JSON-LD `startDate` against visible event-date facts found
      on the same page.
- [ ] Flag any discrepancy ≥1 day.
- **Severity:** high if >7 days apart, else medium. **Confidence: high**
  - this is a direct field comparison, not a heuristic.
- **Why this matters:** an AI agent reading structured data vs. reading
  the visible page could report two different dates for the same event -
  which representation it reads depends on the pipeline, not the fact.

### FR005 — Structured `dateModified` vs. visible "last updated" text
- [ ] Same logic as FR003, applied to `dateModified` vs. visible
      "updated"-type facts.
- [ ] Flag discrepancies ≥3 days (looser threshold than FR003 - update
      timestamps drift by small amounts more innocuously than event dates).
- **Severity:** medium. **Confidence: high.**

### FR007 — Fake-freshness signal (inferred)
- [ ] Only considers `dateModified` values within the last 14 days
      ("recent").
- [ ] Checks whether the same page still has an unresolved stale
      deadline/event fact (same criteria as FR001/FR002, minus the
      acknowledgement check already applied).
- [ ] Flag if both are true.
- **Severity:** medium. **Confidence: medium** - this is inference (a
  recent-looking timestamp plus an unrelated unresolved fact), not proof.
  FR013 is the direct-evidence version of the same idea, available when a
  previous snapshot exists; use FR007 as the fallback when it doesn't.
- **Why this matters:** per Google's own stated guidance, a date bump
  without a substantive change is a distinct, deliberately detectable
  failure mode - not the same thing as staleness itself, and a source
  caught doing it loses trust in its freshness signals more broadly.

### FR010 — Expired `Offer.validThrough` still shown as available
- [ ] Only applies when a JSON-LD `Offer` has a `validThrough` field.
- [ ] Flag if `validThrough` has passed AND (the page has purchase-CTA
      language like "add to cart"/"buy now" OR the `availability` field
      isn't `OutOfStock`/`Discontinued`, OR there's no availability field
      to rule it out at all).
- [ ] Skip if the page already reflects the offer as unavailable.
- **Severity:** high if >14 days past, else medium. **Confidence: high**
  - `validThrough` is a structured field designed exactly for this
  purpose, not a text heuristic.

### FR011 — Stale footer copyright year
- [ ] Extract the latest year from a `© YYYY` / `Copyright YYYY` /
      `© YYYY-YYYY` pattern anywhere on the page.
- [ ] Flag if ≥365 days behind the current year.
- **Severity: low. Confidence: low** - deliberately weak on its own
  (easy to forget even on well-maintained sites, not tied to actual
  content changes), but cheap to check and a commonly used quick
  maintenance heuristic.

---

## CROSS-RESOURCE CONSISTENCY

### FR004 — Cross-resource conflict (the ACIFFS-style check)
- [ ] Across ALL sources passed into one audit run, group deadline/event
      facts by resolved date.
- [ ] If the same fact type resolves to 2+ distinct dates AND those dates
      come from genuinely different sources (not just two mentions on the
      same page - that's FR005's territory), flag.
- [ ] Compute a crude relatedness score: shared 5+-letter vocabulary
      between the two snippets, as a proxy for "are these plausibly
      describing the same named deadline/event." Confidence is high at
      ≥15% overlap, medium below that (and the evidence text explicitly
      says so, since two coincidentally-worded but unrelated deadlines
      could otherwise look like a false match).
- **Severity:** always high - regardless of relatedness confidence, if an
  agent could retrieve either source and get a different answer for what
  reads like the same fact, that's a real integrity risk worth surfacing,
  even if a human needs to confirm relatedness.

---

## CRAWL-FRESHNESS SIGNAL PLAUSIBILITY (requires `sitemap_entries`)

### FR009 — Sitemap `lastmod` in the future
- [ ] Parse each sitemap entry's `lastmod`.
- [ ] Flag any entry dated after today.
- **Severity: medium. Confidence: high** - unambiguous data-quality bug,
  typically a clock/timezone/generation error.

### FR008 — Suspiciously uniform sitemap `lastmod`
- [ ] Only evaluated when the sitemap has ≥10 entries (too noisy on tiny
      sitemaps).
- [ ] Group entries by exact `lastmod` value.
- [ ] Flag if the most common value covers ≥70% of all entries.
- **Severity: medium. Confidence: medium.**
- **Why this matters:** per Google/Bing guidance, `lastmod` is meant to
  reflect real, per-URL changes. A mass-identical timestamp is the
  fingerprint of an automated bulk "touch" (a CMS migration, or
  deliberate manipulation) rather than genuine content changes - and it's
  specifically the pattern that causes search engines to stop trusting a
  site's `lastmod` values sitewide, not just for the affected URLs.

### FR012 — Sitemap `lastmod` vs. page's own freshness signal
- [ ] For any source whose URL also appears in the sitemap, compare the
      sitemap's `lastmod` against that page's own `dateModified` /
      visible "last updated" text.
- [ ] Flag if the gap is ≥30 days.
- **Severity:** low under 90 days, medium beyond. **Confidence: medium.**
- **Why this matters:** two freshness signals for the same page
  disagreeing means a downstream system has no way to know which to
  trust - independent of which one (if either) is actually correct.

---

## SNAPSHOT-BASED FRESHNESS (requires `previous_snapshot`)

Background: `compute_snapshot(html, url)` returns a small, storable
fingerprint (a content hash of normalized visible text, a text length, a
metadata hash covering title/description/canonical/dateModified/
datePublished) - not the full page text, to keep it cheap to persist
across many URLs over time. "How much changed" is therefore approximated
via length delta, not a true diff; see FR015 for how that approximation is
used and its confidence implications.

Visual (pixel-level rendered) diffing and hidden/JS-injected content
diffing are explicitly OUT of scope here - both depend on a rendered DOM,
which is crawl-render-audit's domain. Diffing the same raw HTML twice
would just re-detect what that skill already flags once, not add new
information.

### FR013 — `dateModified` advanced with zero text change (proven)
- [ ] Requires both a previous and current snapshot with different
      `dateModified` values.
- [ ] Flag only if the text hash is identical between the two snapshots.
- **Severity: high. Confidence: high** - this is the direct-evidence
  version of FR007: not an inference from an unresolved fact, but proof
  via exact hash match that literally nothing in the visible text changed
  while the freshness signal moved.

### FR014 — Metadata-only change
- [ ] Same "text hash identical" precondition as FR013, but doesn't
      require a `dateModified` change specifically - flags if title,
      description, or canonical URL changed while text stayed the same.
- [ ] If only the date fields changed (no title/description/canonical
      diff), that's FR013's territory, not this one - don't double-report.
- **Severity: low. Confidence: medium** - broader and gentler than FR013;
  a metadata-only edit is often legitimate (an SEO tweak), just worth
  surfacing distinctly from a real content update.

### FR015 — Substantial content change, no freshness signal moved
- [ ] Requires the text hash to differ between snapshots (a real change
      happened).
- [ ] Requires the length delta to be both ≥50 characters AND ≥3% of the
      previous length - filters out trivial copy edits that don't
      represent a meaningful update.
- [ ] Flag only if `dateModified` did NOT change between the two
      snapshots (if it did move, that's the healthy case - not a finding).
- **Severity: medium. Confidence: medium** - the size-delta threshold is
  a coarse proxy for "significant," not a true diff, so evidence should
  be read as "plausibly substantial," not a guaranteed defect.
- **Why this matters:** this is the mirror image of FR013/FR007. A real
  update that never touches its own freshness signal means crawlers/
  agents deciding whether to re-fetch this page based on `dateModified`
  may simply never notice the change happened.

---

## General cross-check rules

- Never flag from page age alone. Every check requires either an
  explicit self-declared date attached to the specific fact in question,
  a direct field-vs-field comparison, or a genuine cross-source/cross-
  snapshot contradiction.
- When a check is inference rather than direct evidence (FR007, FR012,
  FR004's relatedness scoring), say so explicitly in the evidence text.
  When it's direct evidence (FR003/FR005/FR010/FR013 - field comparisons
  or exact hash matches), it doesn't need that hedge.
- Don't double-report the same underlying defect through two different
  checks aimed at different evidence (e.g. FR007's inferred version and
  FR013's proven version of the same "fake freshness" story) - if a
  previous snapshot is available and FR013 fires, that's the stronger
  claim; FR007 firing alongside it on the same fact is expected and fine,
  but don't invent additional inferred findings once direct proof exists.
- Out of scope for this skill (handled elsewhere in the marketplace):
  structured-data typing/validity (structured-data-audit), whether a page
  can be crawled/rendered at all (crawl-render-audit), non-text content
  (non-text-audit), visual/pixel-level or JS-injected-content diffing
  (crawl-render-audit's domain, not duplicated here).