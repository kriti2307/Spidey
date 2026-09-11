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

## Check 3 — Broken links, dead-end pages & orphan pages

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
- [ ] If `sitemap.xml` is available, fetch and parse it.
- [ ] Compare sitemap URLs against the set of URLs actually reached via
      internal-link crawling.
- [ ] Flag any sitemap URL never reached through browsing as an
      **orphan page**.

**Severity:**
- Critical — broken link or dead-end reached from the homepage or a
  prominent CTA (booking, contact, purchase actions).
- High — same defect, but reached only from a secondary/nested page.
- Medium — orphan pages (technically fine, but unreachable via normal
  browsing).

**De-duplication rule:** if the same broken URL is linked from multiple
places on the site, report it once with a note of how many places link to
it, rather than one finding per occurrence.

## Check 4 — Mobile usability

*(Requires raw HTML access via a script — cannot be reliably checked via
text-extraction-only tools.)*

- [ ] Check for a `<meta name="viewport" ...>` tag in the page `<head>`.
      Its absence is the single strongest signal of mobile unreadiness.
- [ ] If present, check the tap-target size and spacing of primary
      interactive elements (buttons, links) — flag elements smaller than
      common minimum touch-target guidance or spaced too closely together.
- [ ] Check base font size is legible without requiring zoom (flag
      unusually small base font sizes, e.g. under common minimum body-text
      guidance).

**Severity:**
- Critical — no viewport meta tag at all.
- High — viewport set, but tap targets or font size clearly fail.
- Medium — minor sizing issues on secondary/non-primary elements only.

## Check 5 — Page load performance

*(Requires timing/network-level access via a script.)*

- [ ] Measure time until the page's main content becomes usable (time to
      first meaningful paint, or a reasonable proxy such as response time
      of the main document request).
- [ ] Check for render-blocking resources: large synchronous scripts or
      stylesheets placed before main content in `<head>`.
- [ ] Check for excessively large page payloads, especially unoptimized
      images (large file size relative to displayed dimensions).

**Severity:**
- Critical — load time long enough that a visitor would plausibly abandon
  before content appears.
- High — noticeably slow but the page is still usable.
- Medium — isolated optimization opportunities (e.g. one oversized image)
  that don't affect overall usability.

## Check 6 — Basic accessibility (lightweight subset)

- [ ] Check every meaningful `<img>` has a non-empty `alt` attribute.
      (Decorative images without an `alt` may be acceptable — use
      judgment on whether the image conveys information.)
- [ ] Check every form `<input>`/`<textarea>`/`<select>` has an associated
      visible `<label>` (via `for`/`id` pairing or explicit wrapping).
- [ ] Check the page has exactly one `<h1>` — flag both zero and multiple
      `<h1>` tags as inconsistent heading structure.

**Severity:**
- High — forms with no labels at all (blocks task completion for
  assistive-tech users).
- Medium — missing alt text, or missing/duplicate `<h1>`.

**Framing note:** report missing alt text and heading issues as `type:
opportunity` unless they co-occur with a functional blocker (e.g. a form
with zero labels, which blocks task completion) — treat that case as
`type: issue` instead. This check is a lightweight subset, not full WCAG
compliance; do not over-claim coverage.

## Check 7 — Site search quality

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

## General cross-check rules (apply across all checks)

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