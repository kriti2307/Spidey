# Brand AI-Readiness Audit

**Site:** `https://www.wikipedia.org`
**Audited at:** `2026-09-13T17:44:41Z`

---

## Summary

**Total findings:** 3

🔴 Critical: **0**  
🟠 High: **1**  
🟡 Medium: **1**  
🟢 Low: **1**

## Top Priorities

1. 🟠 **No structured data detected** — `High` (1 affected)
2. 🟡 **Inline SVG graphic has no accessible text equivalent** — `Medium` (1 affected)
3. 🟢 **Page has no canonical URL** — `Low` (1 affected)

## Findings

### 1. 🟠 No structured data detected

**Type:** `Issue`
**Severity:** `High`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.wikipedia.org/`

#### Evidence

> https://www.wikipedia.org/ — No JSON-LD structured data was found on the page.

#### Suggested Action

Add relevant Schema.org structured data.

**Priority:** `High`

---

### 2. 🟡 Inline SVG graphic has no accessible text equivalent

**Type:** `Warning`
**Severity:** `Medium`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.wikipedia.org/`

#### Evidence

> https://www.wikipedia.org/ — Inline <svg> #6 has 2 shape elements (may be an icon, chart, or diagram) but no <title> or aria-label.

#### Suggested Action

Add a <title> or aria-label describing the SVG's content.

**Priority:** `Low`

---

### 3. 🟢 Page has no canonical URL

**Type:** `Issue`
**Severity:** `Low`
**Affected pages/resources:** 1

#### Where it was found

- `https://www.wikipedia.org/`

#### Evidence

> https://www.wikipedia.org/ — No <link rel="canonical"> element was found.

#### Suggested Action

Add a canonical URL that identifies the preferred version of the page.

**Priority:** `Low`

---

_This report is recommendation-only. No changes were made to the audited website._