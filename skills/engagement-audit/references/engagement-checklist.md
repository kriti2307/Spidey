# Engagement Audit — Detailed Checklist

This file contains the exhaustive, line-by-line heuristics behind each check
in `skill.md`. Use this when a specific judgment call needs more detail than
the high-level procedure provides. `skill.md` stays lean; this file holds
the depth.

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
- [ ] Cross-reference destination pages against Check 3's content-emptiness
      test before concluding the nav item "works" — a 200 response alone is
      not sufficient evidence of a good destination.
- [ ] Flag any nav item leading to a broken or content-empty page — **high**
      (this overlaps with Check 3's dead-end/broken-link findings; do not
      double-report the same page as two separate findings — cross-link
      them by ID if both checks fire on the same page).

## Check 2 — Orientation on deep entry

- [ ] Select 1-2 pages that plausibly serve as "answer pages" an AI
      assistant might link a visitor to directly (a specific product,
      service, dish/menu item, or article — not the homepage).
- [ ] Fetch each page directly, without navigating from the homepage first.
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

- [ ] Starting from the homepage, crawl a bounded set of internal pages:
      homepage + all top-level nav destinations + their direct children,
      capped at ~20-30 pages total.
- [ ] Respect `robots.txt` — do not crawl disallowed paths.
- [ ] For every internal link discovered (nav, in-page, footer, CTA), record
      its target URL and the HTTP status returned when fetched.
- [ ] Flag any link returning 4xx/5xx, or any other fetch error, as a
      **broken internal link**.
- [ ] For each crawled page, check outlink count: does it have any internal
      links beyond the site's repeated global nav/footer?
- [ ] For each crawled page, independently check content substance: does the
      page contain unique body text/media beyond a bare heading and the
      repeated nav/footer boilerplate?
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

**Known limitation:** some sites return 4xx to automated clients on
specific paths as anti-bot protection, even though the page works fine for
real visitors. This can't be reliably distinguished from a genuine defect
without a full browser. Treat single-source findings on major/high-traffic
domains with appropriate skepticism.

## Check 4 — Mobile usability (static signals only)

*(Requires raw HTML access via a script — cannot be reliably checked via
text-extraction-only tools. Limited to what's determinable from static
HTML/CSS; no rendering is available to this skill.)*

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
- Critical — no viewport meta tag at all.
- Medium — viewport tag present but missing `width=device-width`, or
  fixed-width elements exceeding the mobile reference width are detected.

## Check 5 — Page load performance

*(Requires timing/network-level access via a script.)*

- [ ] Measure HTTP response time for the initial page request.
- [ ] Measure the HTML payload size (bytes) of the response.
- [ ] Count synchronous `<script src>` and `<link rel="stylesheet">` tags in
      `<head>` (excluding `async`/`defer` scripts) as a static proxy for
      render-blocking risk.
- [ ] Where response headers expose `Content-Length` for linked images,
      flag unusually large image resources (e.g. over ~500KB).

**Severity:**
- Critical — response time far exceeds a reasonable reference threshold
  AND payload/blocking-resource count is also high.
- High — response time alone exceeds the threshold.
- Medium — payload size or blocking-resource count is high but response
  time is otherwise acceptable.

**Evidence must be numeric and specific**, e.g. "returned in 4.8s, payload
1800KB, 17 synchronous script/stylesheet tags in `<head>`" — not a vague
statement like "page seems slow."

## Check 6 — Site search quality

- [ ] Check whether an on-site search feature exists (a search input,
      often in the header, or a dedicated `/search` endpoint).
- [ ] If present, submit a plausible, clearly relevant test query (based on
      content already observed elsewhere on the site) and inspect the
      results.
- [ ] Flag if results are empty, irrelevant, or the search errors out —
      **high**.
- [ ] If no search feature exists:
      - On a small site (few pages, simple nav) — no finding; search may
        reasonably be unnecessary.
      - On a large/multi-category site where nav alone would require many
        clicks to find specific items — report as `type: opportunity`,
        **medium**, suggesting search as a proactive improvement rather
        than treating its absence as a defect.

---

## Known limitations (documented, not silently hidden)

- **Bot-detection / WAF false positives on Check 3.** Some sites return
  4xx (commonly 400 or 403) to automated, non-browser clients on specific
  paths as an anti-bot measure, even though the page works normally for
  real visitors. This skill's static-HTTP approach cannot reliably
  distinguish "genuinely broken for every visitor" from "blocked because
  this looks like a bot" without a full browser (out of scope for this
  skill's declared tools). Confirmed example during testing: a major site's
  `/marketplace`-style page returned HTTP 400 with an empty body to this
  script, while working normally in a real browser. Treat single-source
  broken-link findings on well-known, high-traffic domains with appropriate
  skepticism, and prefer manual spot-checking before treating them as
  confirmed defects.
- **Sitemap/orphan-page detection and generic accessibility checks (alt
  text, heading structure) are intentionally out of scope for this skill**
  — not implemented here because they overlap with the crawlability and
  non-text/structured-data skills owned elsewhere in this marketplace. See
  each check's scope note above for the specific reasoning.
- **Tap-target sizing (mobile) is not assessed** — this requires a rendered
  layout, which is outside this skill's static-HTTP/HTML tool access.

- Do not report the same underlying defect as multiple findings just
  because it was surfaced by more than one check (e.g. a broken link found
  by both Check 1's nav-following and Check 3's crawl) — merge and
  cross-reference by ID instead.
- When a check's fail condition depends on a judgment call (e.g. "is this
  nav label vague," "is this content substantive"), lean toward a lower
  severity or `type: warning`/`opportunity` rather than `type: issue` when
  genuinely uncertain, to keep false-positive risk low.
- Always record the specific URL/page where evidence was observed —
  vague evidence ("navigation is unclear") is not acceptable; the finding
  must be traceable to a specific location.