---
name: engagement-audit
description: >
  Audits a website's on-site engagement — how easily a visitor who arrives
  (often via an AI assistant's answer, not the homepage) can find what they
  came for, navigate without hitting dead ends, and take a clear next step.
  Use when diagnosing why visitors bounce shortly after landing on a site,
  as distinct from why they couldn't find the site in the first place.
license: MIT
allowed-tools: ["web_fetch", "http_get"]
---

# Engagement Audit

## When to use

Use this skill once a target website is known, alongside (not instead of)
discoverability checks. This skill assumes a visitor has already reached the
site — either via the homepage or via a deep link an AI assistant surfaced —
and evaluates whether the site itself keeps them engaged or causes them to
bounce.

Do not use this skill to evaluate crawlability, structured data, or fact
freshness — those are handled by other skills in this marketplace.

> Note: this skill currently implements one check (broken links, dead-end
> pages, and orphan pages). Additional checks (homepage findability, deep-entry
> orientation) will be added incrementally.

## Inputs

- `site_url` (required): the homepage URL of the site to audit.

## Procedure

### Check — Broken links, dead-end pages, and orphan pages

1. Starting from `site_url`, crawl a bounded sample of internal pages
   (recommended: homepage + all top-level nav destinations + their direct
   children, capped at ~20-30 pages, respecting `robots.txt`).
2. For every internal link discovered, record its target URL and the HTTP
   status returned when fetched.
3. Flag any internal link whose target returns a 4xx/5xx (or otherwise
   errors) as a **broken internal link**.
4. For each crawled page, evaluate two things together — do not rely on
   outlink count alone:
   - Does the page have any internal outlinks beyond the site's repeated
     global navigation/footer?
   - Does the page contain substantive unique content (beyond a heading and
     the repeated nav), i.e. is it not empty/placeholder?
   A page failing *both* is a **dead-end page**: it loads successfully but
   gives the visitor nothing to do or see. (This catches pages that return
   200 OK yet are functionally empty — a subtler failure than a broken link.)
5. If a sitemap.xml is available, compare its listed URLs against the set of
   URLs actually reached via internal links during the crawl. Any sitemap
   URL never reached through browsing is an **orphan page** — it exists but
   a visitor could never navigate to it naturally.

**Severity:**
- Critical — broken link or dead-end page reached from the homepage or a
  primary nav item / prominent CTA (e.g. a "Book Now" or "Contact" action).
- High — broken link or dead-end page reached from a secondary/nested page.
- Medium — orphan pages (exist and are technically fine, but unreachable via
  normal browsing).

**Evidence example (from live testing on a real site):**
```json
{
  "id": "F-eng-001",
  "title": "Broken internal link on homepage CTA",
  "severity": "critical",
  "evidence": "Homepage icon link and nav item 'Book Your Event' point to /book.php, which returns a 409 error.",
  "suggested_action": {
    "summary": "Fix the booking endpoint or replace the link with a working booking flow (e.g. a contact form or third-party booking widget).",
    "priority": "critical"
  }
},
{
  "id": "F-eng-002",
  "title": "Dead-end page: Picture Gallery",
  "severity": "high",
  "evidence": "/gallery.htm returns 200 OK and displays a heading ('PICTURE GALLERY - CHEELGADI RESTAURANT') but contains no images or unique content beyond the repeated global navigation.",
  "suggested_action": {
    "summary": "Populate the gallery page with actual images/content, or remove it from the navigation until it is ready.",
    "priority": "high"
  }
}
```

## Output

Emit findings matching the shared marketplace schema: `id`, `title`,
`severity`, `evidence`, `suggested_action` (with `summary` and `priority`).
Do not modify the site or submit any forms with real data — all checks are
read-only (fetch and inspect only).
