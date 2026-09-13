# Brand AI-Readiness Audit

**Site:** `https://www.aciffs.in`
**Audited at:** `2026-09-13T05:12:47Z`

---

## Summary

**Total findings:** 24

🔴 Critical: **0**  
🟠 High: **0**  
🟡 Medium: **18**  
🟢 Low: **6**

## Top Priorities

1. 🟡 **Structured data value not found in visible content: name** — `Medium` (6 affected)
2. 🟡 **Image may contain information that is not available as text** — `Medium` (5 affected)
3. 🟡 **Page lacks a primary heading** — `Medium` (4 affected)

## Findings

### 1. 🟡 Structured data value not found in visible content: name

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 6

#### Where it was found

- `https://www.aciffs.in/`
- `https://www.aciffs.in/about-us`
- `https://www.aciffs.in/publication`
- `https://www.aciffs.in/speakers`
- `https://www.aciffs.in/call-for-papers`
- `https://www.aciffs.in/for-authors/guidelines`

#### Evidence

> https://www.aciffs.in/ — Structured data contains name='ACIFFS 2026 â€“ First International Conference on Advances in Computational Intelligence for Fluid and Fuzzy Systems', but that value was not found in the page's visible text.
> https://www.aciffs.in/about-us — Structured data contains name='ACIFFS 2026 â€“ First International Conference on Advances in Computational Intelligence for Fluid and Fuzzy Systems', but that value was not found in the page's visible text.
> https://www.aciffs.in/publication — Structured data contains name='ACIFFS 2026 â€“ First International Conference on Advances in Computational Intelligence for Fluid and Fuzzy Systems', but that value was not found in the page's visible text.
> https://www.aciffs.in/speakers — Structured data contains name='ACIFFS 2026 â€“ First International Conference on Advances in Computational Intelligence for Fluid and Fuzzy Systems', but that value was not found in the page's visible text.
> https://www.aciffs.in/call-for-papers — Structured data contains name='ACIFFS 2026 â€“ First International Conference on Advances in Computational Intelligence for Fluid and Fuzzy Systems', but that value was not found in the page's visible text.
> https://www.aciffs.in/for-authors/guidelines — Structured data contains name='ACIFFS 2026 â€“ First International Conference on Advances in Computational Intelligence for Fluid and Fuzzy Systems', but that value was not found in the page's visible text.

#### Suggested Action

Verify that the structured-data 'name' value matches the visible page content.

**Priority:** `Medium`

---

### 2. 🟡 Image may contain information that is not available as text

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.aciffs.in/`

#### Evidence

> https://www.aciffs.in/ — Image #3 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.aciffs.in/ — Image #4 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.aciffs.in/ — Image #5 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.aciffs.in/ — Image #6 has no alt text. If it conveys meaningful information, that information may not be available as text.
> https://www.aciffs.in/ — Image #7 has no alt text. If it conveys meaningful information, that information may not be available as text.

#### Suggested Action

Provide a meaningful text alternative when the image conveys important information.

**Priority:** `Medium`

---

### 3. 🟡 Page lacks a primary heading

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 4

#### Where it was found

- `https://www.aciffs.in/about-us`
- `https://www.aciffs.in/publication`
- `https://www.aciffs.in/speakers`
- `https://www.aciffs.in/for-authors/guidelines`

#### Evidence

> https://www.aciffs.in/about-us — No <h1> element was found. 676 visible words were extracted. 9 other headings were found.
> https://www.aciffs.in/publication — No <h1> element was found. 154 visible words were extracted. 4 other headings were found.
> https://www.aciffs.in/speakers — No <h1> element was found. 235 visible words were extracted. 24 other headings were found.
> https://www.aciffs.in/for-authors/guidelines — No <h1> element was found. 292 visible words were extracted. 5 other headings were found.

#### Suggested Action

Add a clear primary heading that identifies the page's main topic.

**Priority:** `Medium`

---

### 4. 🟡 Video may not have captions or a text equivalent

**Type:** `Warning`
**Severity:** `Medium`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.aciffs.in/`

#### Evidence

> https://www.aciffs.in/ — Video element #1 has no <track kind='captions'> element, and no nearby text suggests one exists.
> https://www.aciffs.in/ — Video element #2 has no <track kind='captions'> element, and no nearby text suggests one exists.

#### Suggested Action

Provide captions or a transcript when the video conveys important information.

**Priority:** `Medium`

---

### 5. 🟡 Page navigation failed

**Type:** `Issue`
**Severity:** `Medium`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.aciffs.in/assets/ACIFFS-2026%20abstract_template.docx`

#### Evidence

> https://www.aciffs.in/assets/ACIFFS-2026%20abstract_template.docx — Error type: navigation-error page.goto: Download is starting
Call log:
[2m  - navigating to "https://www.aciffs.in/assets/ACIFFS-2026%20abstract_template.docx", waiting until "domcontentloaded"[22m


#### Suggested Action

Ensure the page can be reached successfully by automated crawlers.

**Priority:** `Medium`

---

### 6. 🟢 Page has no canonical URL

**Type:** `Issue`
**Severity:** `Low`
**Affected pages/resources:** 6

#### Where it was found

- `https://www.aciffs.in/`
- `https://www.aciffs.in/about-us`
- `https://www.aciffs.in/publication`
- `https://www.aciffs.in/speakers`
- `https://www.aciffs.in/call-for-papers`
- `https://www.aciffs.in/for-authors/guidelines`

#### Evidence

> https://www.aciffs.in/ — No <link rel="canonical"> element was found.
> https://www.aciffs.in/about-us — No <link rel="canonical"> element was found.
> https://www.aciffs.in/publication — No <link rel="canonical"> element was found.
> https://www.aciffs.in/speakers — No <link rel="canonical"> element was found.
> https://www.aciffs.in/call-for-papers — No <link rel="canonical"> element was found.
> https://www.aciffs.in/for-authors/guidelines — No <link rel="canonical"> element was found.

#### Suggested Action

Add a canonical URL that identifies the preferred version of the page.

**Priority:** `Low`

---

_This report is recommendation-only. No changes were made to the audited website._