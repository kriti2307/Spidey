---
name: freshness-corroboration
description: >
  Audits time-sensitive information on a website for staleness, expiry,
  and internal contradiction - expired deadlines/events still presented
  as live, prices/hours/availability with a stale self-declared date,
  disagreement between a page's structured data and its own visible text,
  disagreement between genuinely different sources (another page, a
  linked PDF) describing the same fact, implausible sitemap lastmod
  signals, and (when given a previous snapshot) whether the page's own
  freshness claims are backed by an actual content change or are a
  cosmetic date bump. Use when diagnosing why an AI assistant might
  surface an outdated or self-contradictory fact about a brand, or why a
  brand's freshness signals might be distrusted or ignored by crawlers.
license: MIT
allowed-tools: ["web_fetch", "http_get"]
---

# Freshness / Corroboration Audit

## When to use

Use this skill once a target page's HTML (and, optionally, related
resources - another page, a linked PDF, the site's sitemap.xml, or a
previously captured snapshot of the same page) are available. This skill
asks whether time-sensitive facts on the page are current, internally
consistent, and consistent with other sources describing the same fact -
not whether the page is old in general.

Do not use this skill to evaluate structured-data validity/typing
(structured-data-audit), crawlability/JS-rendering (crawl-render-audit),
or non-text content (non-text-audit). This skill only reasons about time:
is a fact still true as stated, and do the sources an agent might pull
this fact from agree with each other.

## Inputs

- `sources` (required): a list of one or more resources to audit together,
  each `{"url", "label", "type": "html"|"pdf"|"text", "content"}`. Pass
  more than one when you have genuinely related resources (a homepage and
  a linked PDF brochure, two official pages stating the same deadline) -
  cross-resource contradiction (FR004) only fires across *different*
  sources, and only helps if you actually give it more than one.
- `today` (optional): date override, defaults to the current date.
- `sitemap_entries` (optional): `[{"url", "lastmod"}, ...]` from
  sitemap.xml. Enables the sitemap-signal checks (FR008/FR009/FR012).
- `previous_snapshot` (optional, per source): a dict previously returned
  by `compute_snapshot()` for that same URL. Enables the snapshot-diff
  checks (FR013/FR014/FR015). This skill does not persist snapshots
  itself - whoever orchestrates repeat audits of the same site is
  responsible for calling `compute_snapshot()` after a run and supplying
  the result back in on the next run.

## Procedure

Checks fall into four groups:

**Facts vs. today** (does the page's own stated time-sensitive fact still hold)
1. Expired deadline still presented as active, no acknowledgement — FR001
2. Past event still promoted with forward-looking language — FR002
3. Self-declared hours/price/availability date is old — FR006

**Same-page consistency** (does the page agree with itself)
4. Structured `startDate` conflicts with visible event date — FR003
5. Structured `dateModified` conflicts with visible "last updated" text — FR005
6. `dateModified` claims a recent update, but an unresolved stale fact
   remains on the page ("fake freshness", inferred) — FR007
7. `Offer.validThrough` expired but item still shown as available — FR010
8. Footer copyright year significantly behind current year — FR011

**Cross-resource consistency** (do independent sources agree)
9. Same fact (deadline/event) resolves to different dates across
   genuinely different sources — FR004

**Crawl-freshness signal plausibility** (sitemap-level, requires `sitemap_entries`)
10. Sitemap `lastmod` values are in the future — FR009
11. A large share of sitemap URLs share one identical `lastmod` (mass-bump
    fingerprint) — FR008
12. A URL's sitemap `lastmod` disagrees with that page's own freshness
    signal — FR012

**Snapshot-based freshness** (requires `previous_snapshot`, direct rather
than inferred evidence)
13. `dateModified` advanced but text hash is unchanged ("fake freshness",
    proven) — FR013
14. Metadata (title/description/canonical) changed, text hash unchanged — FR014
15. Text changed substantially, but no freshness signal reflects it — FR015

See `references/freshness-checklist.md` for full detection logic,
thresholds, and false-positive guardrails behind each check.

## Module layout

This skill's logic is split across three scripts (kept separate because
the file had grown past a single-file-per-skill size, not because each
check needs its own file):
- `scripts/freshness_extraction.py` — date/text parsing, JSON-LD date
  extraction, PDF text extraction, snapshot computation.
- `scripts/freshness_checks.py` — every FR001-FR015 check function.
- `scripts/audit_freshness.py` — the entrypoint: `audit_freshness()`,
  which wires extraction and checks together and is what the marketplace
  entrypoint should actually call.

## Severity guide

- **High** — FR001/FR002 (past 14+ days), FR003 (>7 day discrepancy),
  FR004 (cross-resource conflict), FR010 (expired offer, past 14+ days),
  FR013 (proven fake-freshness).
- **Medium** — most other issue/warning-type findings; severity generally
  scales with how long a fact has been stale or how large a discrepancy is.
- **Low** — FR006/FR011 (early staleness), FR014 (metadata-only change).
- Heuristic/inferred checks (FR007, FR012, and the cross-resource
  relatedness scoring in FR004) note their basis explicitly in evidence
  text; direct-evidence checks (FR013, structured-field checks like FR010)
  don't need that hedge since they're not guesses.

## Output

Emit findings matching the shared marketplace schema: `id`, `title`,
`severity`, `evidence`, `suggested_action` (`summary`, `priority`). This
skill's findings also carry `type` (`issue`/`warning`/`opportunity`) and
`confidence` (`high`/`medium`/`low`) as additive fields. Read-only - this
skill never edits the site; snapshot persistence, if used, is the calling
orchestrator's responsibility, not this skill's. See
`references/example-findings.md` for format/severity calibration examples.