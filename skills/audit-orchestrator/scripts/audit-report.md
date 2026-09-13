# Brand AI-Readiness Audit

**Site:** `https://in.puma.com/in/en/`
**Audited at:** `2026-09-13T15:17:34Z`

---

## Summary

**Total findings:** 34

🔴 Critical: **0**  
🟠 High: **9**  
🟡 Medium: **24**  
🟢 Low: **1**

## Top Priorities

1. 🟠 **Important page content depends on JavaScript** — `High` (8 affected)
2. 🟠 **No structured data detected** — `High` (1 affected)
3. 🟡 **Important content appears after JavaScript rendering** — `Medium` (12 affected)

## Findings

### 1. 🟠 Important page content depends on JavaScript

**Type:** `Issue`
**Severity:** `High`
**Affected pages/resources:** 8

#### Where it was found

- `https://in.puma.com/in/en/bls/bls-asset-fav1`
- `https://in.puma.com/in/en/bls/shop-all-bls`
- `https://in.puma.com/in/en/fathers-day`
- `https://in.puma.com/in/en/fathers-day/fathers-day-gifting`
- `https://in.puma.com/in/en/gifting-guide`
- `https://in.puma.com/in/en/new-in`
- `https://in.puma.com/in/en/outlet`
- `https://in.puma.com/in/en/outlet/outlet-men`

#### Evidence

> https://in.puma.com/in/en/bls/bls-asset-fav1 — 2419 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/bls/shop-all-bls — 2037 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/fathers-day — 2100 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/fathers-day/fathers-day-gifting — 2136 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/gifting-guide — 1922 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/new-in — 2259 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet — 2313 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-men — 2111 additional characters appeared after rendering 24 additional headings appeared after rendering 2 additional links appeared after rendering

#### Suggested Action

Ensure important content is available in the initial HTML response or provide reliable server-side rendering.

**Priority:** `High`

---

### 2. 🟠 No structured data detected

**Type:** `Issue`
**Severity:** `High`
**Affected pages/resources:** 1

#### Where it was found

- `https://in.puma.com/in/en/bls/bls-asset-fav3`

#### Evidence

> https://in.puma.com/in/en/bls/bls-asset-fav3 — No JSON-LD structured data was found on the page.

#### Suggested Action

Add relevant Schema.org structured data.

**Priority:** `High`

---

### 3. 🟡 Important content appears after JavaScript rendering

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 12

#### Where it was found

- `https://in.puma.com/in/en`
- `https://in.puma.com/in/en/bls/bls-asset-fav3`
- `https://in.puma.com/in/en/bls/bls-asset-fav5`
- `https://in.puma.com/in/en/fathers-day/fathers-day-dadtype`
- `https://in.puma.com/in/en/fathers-day/fathers-day-dadtype/fathers-day-dadtype-fit-at-home-dad`
- `https://in.puma.com/in/en/fathers-day/fathers-day-dadtype/fathers-day-dadtype-wfh-dad`
- `https://in.puma.com/in/en/outlet/outlet-kids`
- `https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-pants-and-shorts`
- `https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-t-shirts-and-tops`
- `https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-footwear/outlet-kids-footwear-casual`
- `https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-footwear/outlet-kids-footwear-sandals-and-flip-flops`
- `https://in.puma.com/in/en/outlet/outlet-men/outlet-men-apparel/outlet-men-apparel-jackets`

#### Evidence

> https://in.puma.com/in/en — 330 additional characters appeared after rendering
> https://in.puma.com/in/en/bls/bls-asset-fav3 — 239 additional characters appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/bls/bls-asset-fav5 — 236 additional characters appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/fathers-day/fathers-day-dadtype — 389 additional characters appeared after rendering 2 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/fathers-day/fathers-day-dadtype/fathers-day-dadtype-fit-at-home-dad — 391 additional characters appeared after rendering 2 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/fathers-day/fathers-day-dadtype/fathers-day-dadtype-wfh-dad — 231 additional characters appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-kids — 893 additional characters appeared after rendering 9 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-pants-and-shorts — 458 additional characters appeared after rendering 3 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-t-shirts-and-tops — 407 additional characters appeared after rendering 2 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-footwear/outlet-kids-footwear-casual — 513 additional characters appeared after rendering 3 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-footwear/outlet-kids-footwear-sandals-and-flip-flops — 353 additional characters appeared after rendering 1 additional headings appeared after rendering 2 additional links appeared after rendering
> https://in.puma.com/in/en/outlet/outlet-men/outlet-men-apparel/outlet-men-apparel-jackets — 871 additional characters appeared after rendering 7 additional headings appeared after rendering 2 additional links appeared after rendering

#### Suggested Action

Ensure important page content is available in the initial HTML response rather than relying entirely on client-side rendering.

**Priority:** `Medium`

---

### 4. 🟡 Image may contain information that is not available as text

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 9

#### Where it was found

- `https://in.puma.com/in/en`
- `https://in.puma.com/in/en/bls/bls-asset-fav1`
- `https://in.puma.com/in/en/bls/bls-asset-fav3`
- `https://in.puma.com/in/en/bls/bls-asset-fav5`
- `https://in.puma.com/in/en/bls/shop-all-bls`
- `https://in.puma.com/in/en/fathers-day/fathers-day-dadtype/fathers-day-dadtype-wfh-dad`
- `https://in.puma.com/in/en/outlet/outlet-kids`
- `https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-pants-and-shorts`
- `https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-footwear/outlet-kids-footwear-sandals-and-flip-flops`

#### Evidence

> https://in.puma.com/in/en — Image #28 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/bls/bls-asset-fav1 — Image #25 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/bls/bls-asset-fav3 — Image #3 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/bls/bls-asset-fav3 — Image #5 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/bls/bls-asset-fav5 — Image #8 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/bls/bls-asset-fav5 — Image #10 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/bls/shop-all-bls — Image #27 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/fathers-day/fathers-day-dadtype/fathers-day-dadtype-wfh-dad — Image #1 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/outlet/outlet-kids — Image #12 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-pants-and-shorts — Image #4 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-apparel/outlet-kids-apparel-pants-and-shorts — Image #6 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://in.puma.com/in/en/outlet/outlet-kids/outlet-kids-footwear/outlet-kids-footwear-sandals-and-flip-flops — Image #2 has no alt text. If it conveys meaningful information, that information may not be available as text.

#### Suggested Action

Provide a meaningful text alternative when the image conveys important information.

**Priority:** `Medium`

---

### 5. 🟢 Page has no meta description

**Type:** `Issue`
**Severity:** `Low`
**Affected pages/resources:** 1

#### Where it was found

- `https://in.puma.com/in/en/bls/bls-asset-fav1`

#### Evidence

> https://in.puma.com/in/en/bls/bls-asset-fav1 — No meta description was found.

#### Suggested Action

Add a concise meta description that summarizes the page's main content.

**Priority:** `Low`

---

_This report is recommendation-only. No changes were made to the audited website._