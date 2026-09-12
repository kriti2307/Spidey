---
name: crawlability
description: Audit website crawlability, JavaScript rendering, and HTML discoverability. Use this skill when a website needs to be checked for crawlable pages, HTTP errors, robots.txt restrictions, redirects, sitemap-discovered URLs, JavaScript-dependent content, and important HTML metadata or extracted content.
---

# Crawlability Audit Skill

## Purpose

Audit a website to determine whether important content and pages are
accessible to crawlers and exposed in usable HTML.

This skill covers three areas:

1. Crawlability
2. JavaScript rendering
3. HTML extraction

The skill is read-only. It must not modify the audited website.

## Input

Accept a website URL.

Example:

`https://example.com`

Normalize the URL before crawling.

## Workflow

### Step 1: Crawl the website

Use the crawler implementation:

`scripts/crawler`

The crawler must:

- respect robots.txt
- respect crawl-delay when provided
- stay within the target origin
- avoid non-HTML resources unless explicitly required
- follow internal links
- process sitemap URLs when available
- enforce crawl limits
- rate-limit requests
- record HTTP status codes
- record redirects
- record failed requests

Do not bypass robots.txt restrictions.

### Step 2: Detect JavaScript rendering gaps

Use:

`scripts/renderer/render-gap.js`

Compare the initial HTML response with the rendered page.

Look for important content that appears only after JavaScript execution, including:

- visible text
- headings
- links

Flag a rendering issue when meaningful content is added only after
rendering.

Do not flag small or insignificant DOM differences as a problem.

### Step 3: Extract HTML information

Use:

`scripts/extractor/html-extractor.js`

Extract information needed for the audit, including:

- page title
- meta description
- canonical URL
- headings
- visible text
- hidden text
- semantic HTML elements
- internal and external links
- images and alternative-text metadata

Prefer extracted evidence over assumptions.

### Step 4: Run HTML checks

Use:

`scripts/audit/html-checks.js`

Check for meaningful HTML-level issues such as:

- missing page title
- multiple title elements
- missing primary heading on substantial pages
- missing canonical URL
- invalid or conflicting canonical URL
- missing meta description
- multiple meta descriptions
- extremely small visible text
- substantial hidden content

Only report an issue when the evidence supports it.

### Step 5: Produce findings

Each detected issue must contain:

- title
- severity
- evidence
- suggested action

Evidence must identify the affected URL whenever possible.

Severity levels:

- `critical`
- `high`
- `medium`
- `low`

Use `critical` only for issues that can seriously prevent users or
crawlers from accessing important site functionality.

Use `high` for significant discoverability or rendering problems.

Use `medium` for meaningful but less severe problems.

Use `low` for minor issues or limited improvements.

Do not create findings merely because something could theoretically be
improved.

## JavaScript-specific guidance

A page should be considered problematic when important information is
missing from the initial HTML but appears after JavaScript execution.

Strong evidence includes:

- substantial text added after rendering
- headings added after rendering
- important internal links added after rendering

Example finding:

Title:
`Important page content depends on JavaScript`

Evidence:
`191 additional characters appeared after rendering; 2 additional
headings and 3 additional links appeared after rendering.`

Suggested action:
`Ensure important content is available in the initial HTML response or
provide reliable server-side rendering.`

## Crawlability-specific guidance

Report:

- HTTP 4xx/5xx responses for discovered important pages
- failed requests
- problematic redirects
- robots.txt restrictions affecting crawlable content
- sitemap discovery failures when they materially affect discovery

Do not report a robots.txt-blocked URL as a broken page merely because
the crawler could not fetch it.

Do not crawl outside the target origin.

## HTML extraction guidance

Extract content from the rendered page when rendering is required, but
retain the initial HTML response for comparison.

Use visible content as the primary basis for content-related findings.

Do not treat:

- scripts
- styles
- templates
- clearly hidden elements

as visible page content.

## Output

Return structured findings to the orchestrator.

The orchestrator will convert findings into the final marketplace report.

Do not generate a separate report format inside this skill.

## Safety and scope

This skill is strictly read-only.

Never:

- submit forms
- log into accounts
- change website content
- delete resources
- publish content
- modify configuration
- bypass robots.txt
- intentionally overload a website

Keep crawling within reasonable limits and use rate limiting.

## Implementation

The crawler implementation is organized under:

`scripts/crawler/`

The rendering detector is:

`scripts/renderer/render-gap.js`

The HTML extractor is:

`scripts/extractor/html-extractor.js`

The audit checks are:

`scripts/audit/`

Development and integration tests are kept under:

`scripts/test/`

The crawler combines:

- URL normalization
- robots.txt handling
- sitemap discovery
- page loading
- rate limiting
- JavaScript render-gap detection
- HTML extraction
- crawl checks
- HTML checks

The implementation should remain modular so individual components can
be tested independently.