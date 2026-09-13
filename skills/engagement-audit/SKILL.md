---
name: engagement-audit
description: >
  Audits on-site engagement after a visitor arrives at a website, including
  navigation/findability, deep-page orientation, broken links and dead ends,
  mobile readiness, measurable page-load signals, and on-site search.
  Use when diagnosing why visitors bounce after arriving, including from
  AI-referred deep links.
license: MIT
allowed-tools: http_get
---

# Engagement Audit

## When to use

Use this skill once a target website is known, alongside (not instead of)
discoverability checks.

This skill assumes a visitor has already reached the site — either via the
homepage or via a deep link an AI assistant surfaced — and evaluates whether
the site itself keeps them engaged or causes them to bounce.

Do not use this skill to evaluate crawlability, render gaps, structured data,
or fact freshness. Those are handled by other skills in this marketplace.

---

## Inputs

- `site_url` (required): the homepage URL of the site to audit.
- `entry_pages` (optional): one or more specific deep-page URLs to simulate
  an assistant-referred visitor landing directly on them.

If `entry_pages` is not provided, select 1–2 candidate answer pages from the
homepage-linked offerings and eligible top-level navigation destinations,
subject to the implementation's candidate-selection rules.

---

## Scope

This skill owns six engagement checks:

1. Findability from the homepage
2. Orientation on deep entry
3. Broken links and dead-end pages
4. Static mobile-readiness signals
5. Measurable initial page-load performance signals
6. On-site search quality

The skill intentionally does not own:

- sitemap/orphan-page detection
- crawlability
- render-gap detection
- structured-data validation
- generic accessibility auditing
- visual tap-target sizing
- semantic search-result relevance evaluation

---

## Output schema

Each finding must include:

- `id` — unique identifier, e.g. `F-eng-001`
- `type` — one of:
  - `issue` — clear defect
  - `warning` — risky but not conclusively broken
  - `opportunity` — proactive improvement where no defect is established
- `title`
- `severity` — `critical`, `high`, `medium`, or `low`
- `evidence` — mandatory, non-empty, specific evidence identifying the exact
  URL/page and observation
- `suggested_action`
  - `summary` — one-line description of the fix
  - `steps` — mandatory 2–4 concrete, mechanism-specific actions explaining
    how to implement the fix and why it addresses the underlying cause
  - `priority` — `critical`, `high`, `medium`, or `low`

A finding with vague evidence such as "navigation seems unclear" is invalid.
Retest and obtain a specific observation, or do not report the finding.

Do not emit a finding without traceable evidence.

---

## Mandatory finding rules

### Evidence

Every finding must contain evidence that is:

- specific
- traceable to a URL/page
- based on an observation actually obtained by the implementation

Examples of valid evidence:

- HTTP status code
- exact URL
- extracted character count
- detected or missing HTML element
- exact navigation label
- measured response time
- measured HTML payload size
- count of blocking resources
- image `Content-Length`
- explicit no-results marker

Do not infer defects from visual or semantic assumptions that cannot be
verified through static HTML/HTTP inspection.

Distinguish:

- **not detected** — the parser did not find a signal within its inspection
  scope
- **confirmed absent** — the implementation has sufficient evidence to conclude
  that the signal is absent

If the available evidence is insufficient, mark the relevant check as
unverified rather than inventing evidence.

### Suggested actions

Every finding must contain a mechanism-specific `suggested_action.steps`
array with 2–4 concrete actions.

Do not provide only a generic recommendation such as "fix the navigation."

For example, instead of:

> Fix the broken link.

provide steps explaining how to replace the invalid target, remove the link
when no destination exists, and preserve the user's navigation path.

### Proactive opportunities

Every check must consider whether a genuine, site-specific proactive
improvement applies even when no defect is found.

Do not emit boilerplate opportunities copied across every site.

If no site-specific and non-obvious opportunity is supported by the observed
evidence, emit none.

### Read-only behavior

All checks are read-only.

Do not:

- modify the website
- submit forms with real data
- authenticate
- perform destructive actions
- send messages
- create accounts
- make purchases
- change site state

---

# Procedure

## Check 1 — Findability from homepage

### Goal

Determine whether homepage-highlighted offerings can be reached through clear
navigation.

### Procedure

1. Fetch `site_url`.
2. Identify the site's primary navigation using the available navigation
   selectors.
3. Identify homepage-highlighted offerings using:
   - linked `<h2>` elements
   - linked `<h3>` elements
   - links inside feature/category/highlight containers
4. Exclude:
   - footer headings
   - visually hidden headings
   - unlinked headings
5. Identify detected top-level navigation links.
6. Identify detected submenu links one level below the primary navigation.
7. Compare each homepage-highlighted offering URL with the detected navigation
   URLs.
8. Flag an offering with no corresponding navigation path.
9. Flag an offering that appears only in detected submenu navigation rather than
   top-level navigation.
10. Compare top-level navigation labels against the implementation's generic
    label list.
11. Validate up to three same-domain top-level navigation destinations when
    their crawl results are already available.
12. Treat a successful sampled destination with fewer than 150 characters of
    extracted text as content-thin.
13. Cross-reference broken/content-thin navigation destinations with the
    broken-link analysis in Check 3 to avoid unnecessary duplication.
14. If no defect is found, consider a site-specific grouping or navigation
    opportunity based on the offerings actually observed.

### Generic navigation labels

The implementation explicitly checks labels such as:

- `home`
- `menu`
- `more`
- `other`
- `misc`
- `info`
- `page`
- `about`
- `contact`
- `login`
- `sign in`
- `sign up`
- `cart`

A matching generic label is a **medium** finding when it makes the navigation
destination insufficiently descriptive.

### Severity

- **Critical** — a homepage-highlighted offering has no detected navigation
  path.
- **High** — a sampled navigation destination is broken or content-thin.
- **Medium** — an offering is only represented in submenu navigation, or a
  top-level navigation label matches the generic-label list.
- **Low** — proactive grouping/navigation opportunity where no defect exists.

---

## Check 2 — Orientation on deep entry

### Goal

Determine whether a visitor who lands directly on an internal page can
understand where they are and what they can do next without first visiting the
homepage.

### Procedure

1. Select 1–2 candidate answer pages.
2. Prioritize:
   - homepage-linked featured offerings
   - eligible top-level navigation destinations
3. Exclude obvious non-content paths such as:
   - about
   - contact
   - privacy
   - terms
   - login
   - signin
   - signup
   - cart
   - checkout
   - account
4. When `entry_pages` is explicitly provided, use those pages.
5. When running through the orchestrator, reuse pages already collected by
   crawlability rather than performing another crawl/request.
6. Detect orientation cues using:
   - breadcrumb-related classes
   - breadcrumb `aria-label` values
   - breadcrumb navigation
   - visible parent links
   - `rel="up"`
   - classes containing `parent`
   - classes containing `back`
7. Determine whether the page is sufficiently self-explanatory.
8. The implementation uses this proxy:
   - a non-empty `<h1>`
   - more than 300 characters of extracted text after removing
     header/navigation/footer boilerplate
9. Count links outside navigation and footer chrome as a proxy for next-step
   or related-content availability.
10. More than two such links is treated as a positive next-step signal.
11. If no defect exists, consider a site-specific proactive improvement based
    on the actual deep-page content.

### Important limitation

The implementation does not semantically determine whether a link is a CTA,
order button, related-content link, contact action, or another particular
conversion action.

It uses the count of non-navigation/non-footer links as a proxy.

### Severity

- **Critical** — no orientation cue AND insufficient standalone content.
- **High** — no orientation cue, but standalone content passes the
  `<h1>` + 300-character proxy.
- **Medium** — orientation cue exists, but there are 0–2 links outside
  navigation/footer chrome.
- **Low** — orientation and next-step signals are present, with a possible
  site-specific improvement.

---

## Check 3 — Broken links and dead-end pages

### Goal

Determine whether visitors who land on analyzed pages can continue somewhere
useful.

Sitemap/orphan-page detection is intentionally outside this check. That
belongs to crawlability/discoverability.

### Orchestrator mode

When crawlability artifacts are available:

1. Reuse the pages and link/status information already collected.
2. Do not perform a second crawl.
3. Compare internal link targets against known crawl statuses.
4. Treat unknown targets as unverified rather than independently fetching them.
5. Scan analyzed pages for internal links outside navigation/header/footer
   chrome.
6. Measure substantive visible text after removing navigation/header/footer
   boilerplate.
7. Treat a page as a dead end only when:
   - it has no internal outlinks beyond chrome, AND
   - it has fewer than 250 characters of substantive visible text.

### Standalone mode

When no crawl artifact is supplied, retain the bounded fallback crawl.

- Maximum crawl size: 25 pages.
- Respect `robots.txt`.
- Record internal link targets and their HTTP statuses.

### Broken links

Flag known internal targets returning 4xx/5xx or another recorded fetch error.

Report at most 10 broken internal-link targets in one run.

Normalize URLs so repeated links to the same broken target do not generate
duplicate findings.

### Severity

- **Critical** — a broken internal link whose target is linked directly from
  the homepage.
- **High** — a broken internal link whose target is linked from a secondary
  page.
- **Medium** — a page with no useful internal outlinks beyond navigation,
  header, and footer chrome AND fewer than 250 characters of substantive
  visible content.

### False-positive limitation

Some sites return 4xx responses to automated non-browser clients as an
anti-bot/WAF measure even though the page works for normal visitors.

The implementation cannot reliably distinguish this from a genuine broken
page without browser-level verification.

Treat isolated broken-link findings on major/high-traffic domains with
appropriate skepticism.

---

## Check 4 — Mobile usability

### Goal

Detect static HTML/CSS signals suggesting a likely non-responsive mobile
experience.

This check does not render the page.

### Procedure

1. Inspect the page for a viewport meta tag.
2. Flag a missing viewport tag.
3. If a viewport tag exists, check whether it includes
   `width=device-width`.
4. Inspect inline `style` attributes and `<style>` blocks for numeric
   declarations in the form:
   `width: Npx`
5. Flag numeric fixed widths greater than the 414px mobile reference width.
6. Do not attempt to assess:
   - tap-target size
   - spacing
   - actual responsive behavior
   - visual readability

These require rendering and are outside this skill's available inspection
method.

### Severity

- **Medium** — no viewport meta tag.
- **Medium** — viewport exists but does not include `width=device-width`.
- **Medium** — fixed-width CSS declarations greater than 414px are detected.

---

## Check 5 — Page-load performance

### Goal

Use measurable HTTP/HTML signals to identify potentially slow or resource-heavy
initial page loads.

### Procedure

1. Use the initial page request when response timing is available.
2. When crawlability supplies the HTML artifact without navigation timing,
   mark response-time measurement as unverified instead of issuing a duplicate
   request solely for timing.
3. Measure HTML payload size in bytes/KB.
4. Count synchronous `<script src>` elements in the page `<head>`, excluding
   scripts marked `async` or `defer`.
5. Count stylesheet `<link>` elements in the `<head>`.
6. Treat the following as heavy-resource signals:
   - HTML payload > 1500KB
   - more than 10 blocking script/stylesheet tags
7. Check up to the first 15 homepage `<img>` resources using read-only HEAD
   requests.
8. Flag images whose `Content-Length` exceeds 500KB.
9. If no higher-severity issue exists, consider whether the measured timing
   supports a site-specific low-severity performance opportunity.

### Thresholds

- Slow response: **>= 3.0 seconds**
- Borderline response: **>= 1.5 seconds and < 3.0 seconds**
- Heavy HTML payload: **> 1500KB**
- Heavy blocking-resource count: **> 10**
- Large image: **> 500KB**

### Severity

- **Critical** — response time >= 3.0s AND either HTML payload exceeds
  1500KB or blocking resources exceed 10.
- **High** — response time >= 3.0s.
- **Medium** — HTML payload exceeds 1500KB OR blocking-resource count exceeds
  10.
- **Medium** — an individual homepage image exceeds 500KB.
- **Low** — response time >= 1.5s but < 3.0s and no higher-severity condition
  applies.

### Evidence

Evidence must contain numeric observations.

Good:

> `https://example.com/ returned in 3.7s with 1750KB HTML and 12 blocking
> script/stylesheet tags.`

Bad:

> `The page seems slow.`

---

## Check 6 — Site search quality

### Goal

Determine whether a site has usable on-site search signals and, when safely
possible, perform a limited read-only search test.

### Search detection

Detect search UI using:

- `input[type="search"]`
- `[role="search"]`
- forms whose action contains `search`
- inputs whose name contains `search`

### If no search is detected

Count homepage featured offerings.

- If more than 8 featured offerings exist, report a **medium opportunity**
  for site search.
- If 8 or fewer featured offerings exist, do not report missing search as a
  defect or finding.

### If search UI is detected

1. Determine whether a GET-based search action is exposed.
2. Confirm that an identifiable query parameter exists.
3. Derive one query term from content already observed on the site.
4. Perform one safe GET request using that query term.
5. Do not submit forms with side effects.
6. Do not authenticate.
7. Do not make multiple search requests simply to improve confidence.

### Search result assessment

Flag a **high** finding when:

- the tested search endpoint errors, or
- the endpoint returns a 4xx/5xx response, or
- the returned page contains an explicit no-results marker such as:
  - `no results`
  - `0 results`
  - `nothing found`
  - `no matches`

The implementation does **not** semantically evaluate whether returned results
are relevant to the query.

Therefore, do not claim that semantic search relevance has been verified.

### Search present but untestable

If search UI is detected but no safe GET endpoint and identifiable query
parameter can be established:

- mark search quality as unverified
- emit a low opportunity when appropriate
- do not invent a search-quality result

---

# Known limitations

- **Deep-entry candidate selection is heuristic.** The implementation
  prioritizes linked homepage offerings and then eligible top-level navigation
  destinations while excluding obvious non-content paths.

- **Orchestrator mode reuses crawlability artifacts.** Pages that are not
  already present in those artifacts are not silently fetched by engagement.

- **Response timing may be unavailable in orchestrator mode.** The crawl
  artifact supplies HTML and status information but does not necessarily
  contain navigation timing.

- **Static mobile checks cannot verify actual visual responsiveness.** A
  viewport tag or absence of large fixed-width declarations does not guarantee
  a good mobile experience.

- **Tap-target sizing is out of scope.** It requires rendered layout
  inspection.

- **Search relevance is not semantically evaluated.** The search check only
  performs the limited safe GET test and looks for endpoint errors or explicit
  no-results markers.

- **Unknown internal links are not independently fetched in orchestrator
  mode.** They are recorded as unverified.

- **Broken-link findings may be affected by bot protection/WAF behavior.**
  Automated HTTP clients can receive errors that ordinary browsers do not.

- **The 150-character navigation threshold is a content-thinness proxy.**
  A short page is not necessarily defective, so findings should be interpreted
  with the specific URL and evidence in mind.

- **The 300-character deep-entry threshold is a self-explanation proxy.**
  It does not semantically determine whether a human would consider the page
  understandable.

- **The 250-character dead-end threshold is a heuristic.**
  It identifies pages with both little substantive content and no useful
  internal outlinks, rather than proving that every visitor will be unable to
  continue.

- **Do not duplicate the same underlying defect across checks.** When multiple
  checks identify the same broken target or root cause, consolidate or
  cross-reference the findings.

- When evidence is uncertain, prefer `warning`, `opportunity`, a lower
  severity, or `unverified` rather than asserting a defect that cannot be
  reliably established.

---

# Final validation before emitting findings

For every finding, confirm:

- The URL/page is explicitly identified.
- Evidence contains a specific observed fact.
- The severity is supported by the check's thresholds.
- `suggested_action.summary` describes the root fix.
- `suggested_action.steps` contains 2–4 mechanism-specific implementation
  actions.
- The finding does not duplicate another finding for the same underlying
  defect.
- The finding does not rely on rendering or semantic assumptions unavailable
  to this skill.
- The check was considered for a genuine site-specific proactive opportunity,
  even when no defect was found.

All auditing actions must remain read-only.
