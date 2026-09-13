# Brand AI-Readiness Audit

**Site:** `https://www.nike.in/`
**Audited at:** `2026-09-13T15:32:27Z`

---

## Summary

**Total findings:** 46

🔴 Critical: **1**  
🟠 High: **0**  
🟡 Medium: **38**  
🟢 Low: **7**

## Top Priorities

1. 🔴 **Homepage-highlighted offerings missing from navigation** — `Critical` (1 affected)
2. 🟡 **Important content appears after JavaScript rendering** — `Medium` (19 affected)
3. 🟡 **Image may contain information that is not available as text** — `Medium` (14 affected)

## Findings

### 1. 🔴 Homepage-highlighted offerings missing from navigation

**Type:** `Issue`
**Severity:** `Critical`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.nike.in/`

#### Evidence

> https://www.nike.in/ — https://www.nike.in/: homepage-linked offerings have no matching top-level or submenu navigation link: ["'DON’T LOSE YOUR COOL' -> https://www.nike.in/don-t-lose-your-cool/c/111353", "'ELEVATE YOUR PRE-GAME ROUTINE' -> https://www.nike.in/nike-24-7/c/113240"].

#### Suggested Action

Add navigation paths for important homepage-highlighted offerings.

**Steps:**

- Cross-reference homepage offering URLs against navigation targets.
- Add a top-level or submenu link to every unmatched offering.
- Re-run the crawl to confirm each offering is reachable through navigation.

**Priority:** `Critical`

---

### 2. 🟡 Important content appears after JavaScript rendering

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 19

#### Where it was found

- `https://www.nike.in/new-arrivals/c/94475`
- `https://www.nike.in/best-sellers/c/94167`
- `https://www.nike.in/top-picks-under-4999/c/94477`
- `https://www.nike.in/just-do-the-work/c/94478`
- `https://www.nike.in/retro-running/c/94175`
- `https://www.nike.in/acg/c/111979`
- `https://www.nike.in/air-force-1/c/94020`
- `https://www.nike.in/air-jordan-1/c/94019`
- `https://www.nike.in/air-max/c/94031`
- `https://www.nike.in/dunk/c/94027`
- `https://www.nike.in/nike-pegasus-shoes/c/99874`
- `https://www.nike.in/nike-vomero-shoes/c/99877`
- `https://www.nike.in/lp/running-desktop`
- `https://www.nike.in/lp/training-desktop`
- `https://www.nike.in/lp/sportswear-desktop`
- `https://www.nike.in/nike-football/c/94823`
- `https://www.nike.in/nike-basketball/c/94822`
- `https://www.nike.in/shop-all-sale/c/99440`
- `https://www.nike.in/all-condition-gear/c/94468`

#### Evidence

> https://www.nike.in/new-arrivals/c/94475 — 587 additional characters appeared after rendering
> https://www.nike.in/best-sellers/c/94167 — 581 additional characters appeared after rendering
> https://www.nike.in/top-picks-under-4999/c/94477 — 596 additional characters appeared after rendering
> https://www.nike.in/just-do-the-work/c/94478 — 559 additional characters appeared after rendering
> https://www.nike.in/retro-running/c/94175 — 498 additional characters appeared after rendering
> https://www.nike.in/acg/c/111979 — 468 additional characters appeared after rendering
> https://www.nike.in/air-force-1/c/94020 — 464 additional characters appeared after rendering
> https://www.nike.in/air-jordan-1/c/94019 — 452 additional characters appeared after rendering
> https://www.nike.in/air-max/c/94031 — 495 additional characters appeared after rendering
> https://www.nike.in/dunk/c/94027 — 450 additional characters appeared after rendering
> https://www.nike.in/nike-pegasus-shoes/c/99874 — 478 additional characters appeared after rendering
> https://www.nike.in/nike-vomero-shoes/c/99877 — 500 additional characters appeared after rendering
> https://www.nike.in/lp/running-desktop — 209 additional characters appeared after rendering
> https://www.nike.in/lp/training-desktop — 283 additional characters appeared after rendering
> https://www.nike.in/lp/sportswear-desktop — 202 additional characters appeared after rendering
> https://www.nike.in/nike-football/c/94823 — 567 additional characters appeared after rendering
> https://www.nike.in/nike-basketball/c/94822 — 593 additional characters appeared after rendering
> https://www.nike.in/shop-all-sale/c/99440 — 671 additional characters appeared after rendering
> https://www.nike.in/all-condition-gear/c/94468 — 447 additional characters appeared after rendering

#### Suggested Action

Ensure important page content is available in the initial HTML response rather than relying entirely on client-side rendering.

**Priority:** `Medium`

---

### 3. 🟡 Image may contain information that is not available as text

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 8

#### Where it was found

- `https://www.nike.in/new-arrivals/c/94475`
- `https://www.nike.in/best-sellers/c/94167`
- `https://www.nike.in/acg/c/111979`
- `https://www.nike.in/lp/running-desktop`
- `https://www.nike.in/lp/training-desktop`
- `https://www.nike.in/lp/sportswear-desktop`
- `https://www.nike.in/nike-football/c/94823`
- `https://www.nike.in/all-condition-gear/c/94468`

#### Evidence

> https://www.nike.in/new-arrivals/c/94475 — Image #38 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/new-arrivals/c/94475 — Image #39 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/best-sellers/c/94167 — Image #40 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/acg/c/111979 — Image #29 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/acg/c/111979 — Image #30 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/lp/running-desktop — Image #20 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/lp/running-desktop — Image #21 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/lp/training-desktop — Image #9 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/lp/training-desktop — Image #10 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/lp/sportswear-desktop — Image #14 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/lp/sportswear-desktop — Image #15 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/nike-football/c/94823 — Image #41 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/all-condition-gear/c/94468 — Image #23 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.nike.in/all-condition-gear/c/94468 — Image #24 has no alt text. If it conveys meaningful information, that information may not be available as text.

#### Suggested Action

Provide a meaningful text alternative when the image conveys important information.

**Priority:** `Medium`

---

### 4. 🟡 Inline SVG graphic has no accessible text equivalent

**Type:** `Warning`
**Severity:** `Medium`
**Affected pages/resources:** 3

#### Where it was found

- `https://www.nike.in/`
- `https://www.nike.in/new-arrivals/c/94475`
- `https://www.nike.in/lp/running-desktop`

#### Evidence

> https://www.nike.in/ — Inline <svg> #8 has 2 shape elements (may be an icon, chart, or diagram) but no <title> or aria-label.
> https://www.nike.in/new-arrivals/c/94475 — Inline <svg> #4 has 4 shape elements (may be an icon, chart, or diagram) but no <title> or aria-label.
> https://www.nike.in/lp/running-desktop — Inline <svg> #6 has 2 shape elements (may be an icon, chart, or diagram) but no <title> or aria-label.

#### Suggested Action

Add a <title> or aria-label describing the SVG's content.

**Priority:** `Low`

---

### 5. 🟡 Canonical URL points to a different page

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.nike.in/new-arrivals/c/94475`

#### Evidence

> https://www.nike.in/new-arrivals/c/94475 — Page URL: https://www.nike.in/new-arrivals/c/94475 Canonical URL: https://www.nike.in/new-featured/c/94475?p=1

#### Suggested Action

Set the canonical URL to the preferred version of this page.

**Priority:** `Medium`

---

### 6. 🟡 Fixed-width elements exceeding mobile viewport

**Type:** `Warning`
**Severity:** `Medium`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.nike.in/`

#### Evidence

> https://www.nike.in/ — https://www.nike.in/: found 23 fixed widths greater than 414px, e.g. [('<style> block', '1920'), ('<style> block', '1920'), ('<style> block', '1200'), ('<style> block', '1300'), ('<style> block', '1440')].

#### Suggested Action

Replace fixed pixel widths with responsive layout rules.

**Steps:**

- Use percentage, max-width, Grid, or Flexbox-based sizing.
- Add a mobile breakpoint where necessary.
- Re-test the page on narrow screens.

**Priority:** `Medium`

---

### 7. 🟢 CSS background-image detected with no adjacent text

**Type:** `Issue`
**Severity:** `Low`
**Affected pages/resources:** 4

#### Where it was found

- `https://www.nike.in/`
- `https://www.nike.in/lp/running-desktop`
- `https://www.nike.in/lp/training-desktop`
- `https://www.nike.in/lp/sportswear-desktop`

#### Evidence

> https://www.nike.in/ — Element uses a CSS background-image ('https://images-static.nykaa.com/fashion-images/pub/media/nike-images/nike/dweb_2008.png_1?tr=w-1536') and has no text content. This cannot be reliably classified as decorative vs. informative from static HTML alone -- flagged for manual review.
> https://www.nike.in/lp/running-desktop — Element uses a CSS background-image ('https://images-static.nykaa.com/fashion-images/pub/media/nike-images/nike/still_motion_2606_dweb.jpg?tr=w-1536') and has no text content. This cannot be reliably classified as decorative vs. informative from static HTML alone -- flagged for manual review.
> https://www.nike.in/lp/training-desktop — Element uses a CSS background-image ('https://images-static.nykaa.com/fashion-images/pub/media/nike-images/nike/dweb_2008_1.png?tr=w-1536') and has no text content. This cannot be reliably classified as decorative vs. informative from static HTML alone -- flagged for manual review.
> https://www.nike.in/lp/sportswear-desktop — Element uses a CSS background-image ('https://images-static.nykaa.com/fashion-images/pub/media/nike-images/Banner/Sports_Desktop.jpg?tr=w-1536') and has no text content. This cannot be reliably classified as decorative vs. informative from static HTML alone -- flagged for manual review.

#### Suggested Action

Manually verify: if this image conveys information, provide a text equivalent nearby.

**Priority:** `Low`

---

### 8. 🟢 URL redirects to another page

**Type:** `Issue`
**Severity:** `Low`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.nike.in/new-arrivals/c/94475`

#### Evidence

> https://www.nike.in/new-arrivals/c/94475 — Requested: https://www.nike.in/new-arrivals/c/94475 Final: https://www.nike.in/new-featured/c/94475

#### Suggested Action

Prefer linking directly to the final destination URL.

**Priority:** `Low`

---

### 9. 🟢 Page has no meta description

**Type:** `Issue`
**Severity:** `Low`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.nike.in/new-arrivals/c/94475`

#### Evidence

> https://www.nike.in/new-arrivals/c/94475 — No meta description was found.

#### Suggested Action

Add a concise meta description that summarizes the page's main content.

**Priority:** `Low`

---

### 10. 🟢 Video may not have captions or a text equivalent

**Type:** `Warning`
**Severity:** `Low`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.nike.in/`

#### Evidence

> https://www.nike.in/ — Video element #1 has no <track kind='captions'> element, and nearby text loosely suggests captions/transcript may exist (keyword match only -- verify manually).

#### Suggested Action

Provide captions or a transcript when the video conveys important information.

**Priority:** `Low`

---

_This report is recommendation-only. No changes were made to the audited website._