---
name: crawlability
description: Audits website crawlability and machine-readable HTML by crawling reachable pages, respecting robots.txt, detecting crawl failures and redirect issues, comparing raw HTML with JavaScript-rendered content, and extracting important page-level HTML signals.
---

# Crawlability Audit Skill

## Purpose

Use this skill to audit whether website pages can be reached and meaningfully understood by automated crawlers and AI systems.

The skill performs read-only analysis. It must not modify the target website.

## When to use

Use this skill when the user asks to audit a website for:

- crawlability
- crawler access problems
- HTTP errors
- redirect problems
- robots.txt restrictions
- sitemap discovery
- JavaScript-rendered content
- important content missing from raw HTML
- page-level HTML extraction issues
- missing or duplicate title elements
- missing or duplicate meta descriptions
- canonical URL problems
- missing primary headings
- very little visible text
- hidden page content
- missing image alternative text

## Audit workflow

1. Start from the supplied website URL.
2. Respect the site's `robots.txt` rules for the crawler user-agent.
3. Respect any crawl delay specified by `robots.txt`.
4. Discover sitemap URLs when available.
5. Crawl reachable same-origin HTML pages.
6. Normalize URLs to avoid duplicate crawling caused by fragments and common tracking parameters.
7. Record HTTP status, final URL, redirects, and navigation failures.
8. Compare raw HTML content with JavaScript-rendered content.
9. Extract page-level HTML information from the rendered page.
10. Run the crawlability, rendering, and HTML checks.
11. Return findings with evidence, severity, and recommended actions.

## Findings

Each finding should contain:

- `type`
- `severity`
- `url`
- `title`
- `evidence`
- `recommendation`

Severity levels:

- `high` — likely prevents or significantly harms crawling or access
- `medium` — important issue that may reduce machine understanding or discoverability
- `low` — smaller issue or quality improvement

Do not report an issue unless there is concrete evidence from the audited page.

## JavaScript rendering

Compare the page before and after JavaScript rendering.

Look for meaningful content that appears only after rendering, including:

- text
- headings
- links

Do not treat small changes or obvious hidden/UI-only content as evidence that important content requires JavaScript.

## HTML extraction

Extract and analyze:

- page title
- title element count
- meta description
- meta description count
- canonical URL
- headings
- visible text
- visible word count
- main content text
- hidden content
- semantic HTML elements
- links
- images and alternative-text information

## Current checks

The skill currently checks for:

### Crawlability

- crawler/network failures
- HTTP error responses
- long redirect chains
- unexpected redirect destinations
- robots.txt blocking

### HTML

- missing title
- multiple title elements
- missing H1 when the page has substantial content and other headings
- missing canonical URL
- canonical URL pointing to another page
- invalid canonical URL
- missing meta description
- multiple meta descriptions
- very little visible text
- substantial hidden content
- images missing alternative text

### JavaScript rendering

- significant text added after rendering
- headings added after rendering
- links added after rendering

## Guardrails

- Read-only analysis only.
- Never modify, submit, delete, or authenticate to the target website.
- Do not bypass robots.txt restrictions.
- Do not intentionally overload a website with requests.
- Prefer same-origin URLs discovered from the supplied website.
- Avoid crawling non-HTML resources such as images, videos, stylesheets, scripts, and downloadable files.
- Use evidence from the actual page rather than assumptions.
- Avoid duplicate findings when the same underlying problem is already represented by a more specific finding.

## Output

Return findings in a structured format suitable for the marketplace orchestrator.

For each finding, include the affected URL, severity, concrete evidence, and a prioritized recommendation.

If no issue is detected for a check, do not create a finding.