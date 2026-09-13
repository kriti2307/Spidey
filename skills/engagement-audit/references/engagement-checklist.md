# Engagement Audit — Detailed Checklist

This file contains the exhaustive, line-by-line heuristics behind each check
in `skill.md`. Use this when a specific judgment call needs more detail than
the high-level procedure provides. `skill.md` stays lean; this file holds
the depth.

## Two execution modes

This skill runs in one of two modes, and several checks behave differently
depending on which:

- **Orchestrator mode** (`crawl_audit` supplied): reuses HTML, URLs, HTTP
  statuses, and robots.txt decisions already collected by the crawlability
  skill's crawl. This skill performs **no second site crawl** in this mode
  — it only makes additional live requests for things crawlability
  genuinely didn't collect (e.g. testing a search endpoint).
- **Standalone mode** (no `crawl_audit`, e.g. running the script directly
  via its CLI): falls back to the skill's original behavior — it performs
  its own bounded, read-only HTTP crawl, since no other skill's crawl data
  is available to reuse.

Each check below notes where its behavior differs between the two modes.

---

## Check 1 — Findability from homepage (nav-driven)

- [ ] List every offering/category/product line the homepage itself
      highlights (headings, featured sections, prominent icons/links).
- [ ] List every top-level nav item.
- [ ] For each homepage-highlighted offering, confirm it has a corresponding
      top-level nav entry, OR is reachable within exactly one submenu click
      from a clearly-labeled parent nav item.
- [ ] Flag any offering with no nav path at all (top-level or one level
      deep) — **critical**.
- [ ] Flag any offering only reachable via an unlabeled or vaguely-labeled
      parent nav item (e.g. generic "Offerings"/"Solutions" hiding specific
      named categories) — **medium**.
- [ ] For each top-level nav label, assess clarity: does the label alone
      indicate what a visitor will find inside? Flag vague labels
      (single buzzwords, no descriptive context) — **medium**.
- [ ] Follow at least 2-3 nav items to their destination pages.
  - **Orchestrator mode:** only nav targets crawlability already visited
    are checked. A nav target crawlability didn't visit is silently
    skipped (not counted toward the 2-3 checked, and not reported as a
    finding of any kind) rather than triggering a second live fetch.
  - **Standalone mode:** each nav target is fetched live (respecting
    `robots.txt`), same as the skill's original behavior.
- [ ] Flag any checked nav item that returns an error status, or whose
      content is under 150 characters of visible text after boilerplate
      removal, as **high**.

## Check 2 — Orientation on deep entry

- [ ] Select 1-2 pages that plausibly serve as "answer pages" an AI
      assistant might link a visitor to directly (a specific product,
      service, dish/menu item, or article — not the homepage), unless
      specific entry pages were supplied.
- [ ] Skip any candidate/supplied URL containing `/fragments/` entirely —
      these are not real visitor-facing pages.
- [ ] **Orchestrator mode:** if a candidate/supplied entry page is not
      among the pages crawlability already crawled, do **not** fetch it —
      mark it `unverified` instead (reason: not present in the crawl
      artifact). This skill never issues its own navigation request for a
      page crawlability didn't already visit while in this mode.
- [ ] **Standalone mode:** fetch each entry page directly, without
      navigating from the homepage first.
- [ ] Check for breadcrumbs (e.g. "Home > Category > Page").
- [ ] Check for any visible parent-category link or "you are here" signal
      distinct from the repeated global nav.
- [ ] Flag missing breadcrumbs/parent-context signals — severity depends on
      the next two checks (see severity table below).
- [ ] Check standalone content completeness: read the page's own text and
      assess whether a visitor with zero prior context (no homepage visit)
      could understand what this page is, what it's about, and (if
      relevant) cost/availability.
- [ ] Flag pages that only make sense with prior homepage context (e.g.
      relies on branding/terminology introduced only on the homepage).
- [ ] Check for a clear next step from the page: a CTA, a "related items"
      section, an add-to-cart/order/contact action, or an obvious path to
      browse further.
- [ ] **Special case:** if the page contains repeated links/actions (e.g.
      "order," "buy," "read more") that all point to the *same* URL across
      many different items, verify that shared URL actually works. A single
      broken shared target repeated across many items should be reported as
      **one finding with elevated severity** (reflecting how many items are
      affected), not as many duplicate findings.
- [ ] Flag missing next-step/CTA — **medium**, unless the page is also
      missing standalone context, in which case escalate (see table).

**Severity table for Check 2:**
| Breadcrumbs/context | Standalone content | Next step | Severity |
|---|---|---|---|
| Missing | Missing | — | Critical |
| Missing | Present | Missing | High |
| Missing | Present | Present | High |
| Present | Present | Missing | Medium |
| Present | Present | Present | Pass (no finding) |

## Check 3 — Broken links & dead-end pages

This check owns: **can a visitor who lands on this page continue somewhere
useful?** Sitemap/orphan-page detection is intentionally NOT part of this
check — that's a crawlability concern (owned by another skill in this
marketplace), not an engagement concern.

- [ ] **Orchestrator mode — no crawling occurs.** This check analyzes only
      the pages crawlability already collected:
  - Build a map of known HTTP status per URL from the crawl artifact.
  - For every internal link found on any already-crawled page, look up its
    target in that known-status map.
  - If the target's status is known and is an error, flag it as a
    **broken internal link** (critical if linked from the homepage, high
    otherwise) — sourced entirely from crawlability's already-collected
    status, not a new request.
  - If a link's target was **not** among the pages crawlability crawled,
    do not guess at its status — record it under `unverified_checks`
    (aggregated as a count, not per-link) instead.
  - Dead-end detection (outlink + content-substance check, see below) is
    evaluated only across the pages crawlability actually crawled.
- [ ] **Standalone mode:** performs its own bounded crawl (homepage +
      top-level nav destinations + their direct children, capped at
      `MAX_CRAWL_PAGES`), respecting `robots.txt`, exactly as in the
      skill's original design — broken-link and dead-end detection both
      apply to pages this check crawls itself in this mode.
- [ ] For each crawled/known page, check outlink count: does it have any
      internal links beyond the site's repeated global nav/footer?
- [ ] For each crawled/known page, independently check content substance:
      does the page contain unique body text/media beyond a bare heading
      and the repeated nav/footer boilerplate?
- [ ] A page failing **both** the outlink check and the content-substance
      check is a **dead-end page** — it loads (200 OK) but gives the visitor
      nothing to do or see.
- [ ] Do not classify a page as dead-end based on outlink count alone — a
      page can have zero unique outlinks but still contain valuable content
      (e.g. a well-written article with no further links). Only flag when
      both signals fail together.

**Severity:**
- Critical — broken link or dead-end reached from the homepage or a
  prominent CTA (booking, contact, purchase actions).
- High — same defect, but reached only from a secondary/nested page.

**De-duplication rule:** if the same broken URL is linked from multiple
places on the site, report it once with a note of how many places link to
it, rather than one finding per occurrence.

**⚠ Open question — possible duplication with crawlability's own findings
(orchestrator mode):** because this check surfaces broken-link findings
using status data crawlability already collected, and crawlability's own
per-page audit likely reports the same broken page from its own
perspective (it visited that URL directly), the same underlying defect may
end up reported twice in the final merged report — once by each skill,
with different titles/evidence text, so the orchestrator's
title+severity+evidence deduplication won't catch it. Worth confirming
with whoever owns crawlability whether this overlap is acceptable (two
framings of the same defect) or should be resolved (e.g. engagement drops
broken-link reporting entirely in orchestrator mode and relies on
crawlability's own findings, using the known-status map only for computing
dead-end/continuation logic internally).

**Known limitation (standalone mode only):** some sites return 4xx to
automated clients on specific paths as anti-bot protection, even though the
page works fine for real visitors. This can't be reliably distinguished
from a genuine defect without a full browser. Treat single-source findings
on major/high-traffic domains with appropriate skepticism.

## Check 4 — Mobile usability (static signals only)

*(Requires raw HTML access — cannot be reliably checked via
text-extraction-only tools. Limited to what's determinable from static
HTML/CSS; no rendering is available to this skill in either mode.)*

- [ ] Get the homepage's HTML — from the crawl artifact in orchestrator
      mode, or via a live fetch in standalone mode (routed through the same
      lookup either way; no behavior difference for this check beyond
      where the HTML comes from).
- [ ] Check for a `<meta name="viewport" ...>` tag in the page `<head>`.
      Its absence is the single strongest signal of mobile unreadiness.
- [ ] Check the viewport tag's `content` includes `width=device-width` —
      flag if present but missing this (e.g. a fixed pixel width instead).
- [ ] Check for fixed-width elements (inline `style` attributes or `<style>`
      blocks) specifying a pixel width greater than a mobile reference
      width (~414px) — a static proxy for likely non-responsive layout.
- [ ] Do NOT attempt to assess tap-target size, spacing, or font
      readability — these require a rendered layout, which is outside this
      skill's declared tool access. Leave this fully out of scope rather
      than approximating it.

**Severity:**
- Medium — no viewport meta tag at all, viewport tag present but missing
  `width=device-width`, or fixed-width elements exceeding the mobile
  reference width are detected.

## Check 5 — Page load performance

- [ ] Get the homepage's HTML and, where available, its response time —
      **orchestrator mode: response time is typically unavailable**, since
      crawlability's crawl artifact doesn't carry navigation timing and
      this check does not issue a duplicate homepage request solely to
      measure it. When this happens, record `unverified` for the
      response-time sub-signal rather than guessing.
  - **Standalone mode:** response time is measured directly from this
    check's own live fetch.
- [ ] Measure the HTML payload size (bytes) — available in both modes,
      since it only requires the HTML already in hand.
- [ ] Count synchronous `<script src>` and `<link rel="stylesheet">` tags in
      `<head>` (excluding `async`/`defer` scripts) as a static proxy for
      render-blocking risk — available in both modes.
- [ ] Where response headers expose `Content-Length` for linked images,
      flag unusually large image resources (e.g. over ~500KB). These are
      resource-level HEAD requests to individual images, not a second page
      crawl, so they run in **both** modes regardless of response-time
      availability.

**Severity:**
- Critical — response time far exceeds a reasonable reference threshold
  AND payload/blocking-resource count is also high. **Only reachable when
  response time is available** (effectively standalone mode, or
  orchestrator mode if that's later extended to supply timing).
- High — response time alone exceeds the threshold. Same availability
  caveat as Critical.
- Medium — payload size or blocking-resource count is high, independent of
  whether response time is available. This is the only severity tier
  reliably reachable in orchestrator mode today.

**Evidence must be numeric and specific**, e.g. "returned in 4.8s, payload
1800KB, 17 synchronous script/stylesheet tags in `<head>`" — or, when
response time is unavailable, state that plainly rather than omitting it
silently (e.g. "response time not measured from the existing crawl
artifact, payload 1800KB, ...").

## Check 6 — Site search quality

- [ ] Check whether an on-site search feature exists (a search input,
      often in the header, or a dedicated `/search` endpoint) — evaluated
      from the homepage HTML already in hand in either mode.
- [ ] If present, and a safe GET-based query can be constructed, submit a
      single plausible, clearly relevant test query (drawn from the site's
      own nav/heading text, not an arbitrary placeholder) and inspect the
      results. This is a single explicit endpoint test, not a crawl, so it
      runs the same way in both modes.
- [ ] Flag if results are empty, irrelevant, or the search errors out —
      **high**.
- [ ] If no safe GET query path can be identified (e.g. only a POST form
      exists), do not submit it — record `unverified` and, if a search UI
      was at least detected, emit a low-severity `opportunity` noting
      quality could not be automatically verified.
- [ ] If no search feature exists at all:
      - On a small site (few pages, simple nav) — no finding; search may
        reasonably be unnecessary.
      - On a large/multi-category site (more than 8 featured offerings)
        where nav alone would require many clicks to find specific items —
        report as `type: opportunity`, **medium**, suggesting search as a
        proactive improvement rather than treating its absence as a defect.

---

## Known limitations (documented, not silently hidden)

- **Response-time signal is typically unverified in orchestrator mode**
  (see Check 5) — this is an intentional tradeoff to avoid a duplicate
  homepage request, not an oversight. Critical/High severity on Check 5
  are effectively unreachable when running through the orchestrator today.
- **Possible duplication with crawlability's own broken-link findings in
  orchestrator mode** (see Check 3's open question above) — not yet
  resolved; flag to the team before final submission.
- **Bot-detection / WAF false positives (standalone mode).** Some sites
  return 4xx (commonly 400 or 403) to automated, non-browser clients on
  specific paths as an anti-bot measure, even though the page works
  normally for real visitors. This skill's static-HTTP approach cannot
  reliably distinguish "genuinely broken for every visitor" from "blocked
  because this looks like a bot" without a full browser. Treat
  single-source broken-link findings on well-known, high-traffic domains
  with appropriate skepticism in standalone mode.
- **Sitemap/orphan-page detection and generic accessibility checks (alt
  text, heading structure) are intentionally out of scope for this skill**
  — not implemented here because they overlap with the crawlability and
  non-text/structured-data skills owned elsewhere in this marketplace.
- **Tap-target sizing (mobile) is not assessed** — this requires a rendered
  layout, which is outside this skill's static-HTTP/HTML tool access in
  either mode.

## General cross-check rules (apply across all checks)

- Do not report the same underlying defect as multiple findings just
  because it was surfaced by more than one check (e.g. a broken link found
  by both Check 1's nav-following and Check 3) — merge and cross-reference
  by ID instead.
- When a check's fail condition depends on a judgment call (e.g. "is this
  nav label vague," "is this content substantive"), lean toward a lower
  severity or `type: warning`/`opportunity` rather than `type: issue` when
  genuinely uncertain, to keep false-positive risk low.
- Always record the specific URL/page where evidence was observed —
  vague evidence ("navigation is unclear") is not acceptable; the finding
  must be traceable to a specific location.
- When a piece of evidence (e.g. response time) is unavailable because of
  the current execution mode rather than because the check failed, say so
  explicitly in the finding/unverified entry — never silently omit it or
  imply it was checked and passed.
