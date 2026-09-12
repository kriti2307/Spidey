Description
Audits a website's on-site engagement — how easily a visitor who arrives (often via an AI assistant's answer, not the homepage) can find what they came for, navigate without hitting dead ends, and take a clear next step. Use when diagnosing why visitors bounce shortly after landing on a site, as distinct from why they couldn't find the site in the first place.

License
MIT

Allowed tools
http_get

Engagement Audit
When to use
Use this skill once a target website is known, alongside (not instead of) discoverability checks. This skill assumes a visitor has already reached the site — either via the homepage or via a deep link an AI assistant surfaced — and evaluates whether the site itself keeps them engaged or causes them to bounce.

Do not use this skill to evaluate crawlability, structured data, or fact freshness — those are handled by other skills in this marketplace.

Inputs
site_url (required): the homepage URL of the site to audit.
entry_pages (optional): one or more specific deep-page URLs to simulate an assistant-referred visitor landing directly on them. If not provided, select 1-2 pages that appear to be "answer" pages discovered during Check 1.
Output schema
Each finding includes:

id — unique identifier (e.g. F-eng-001)
type — one of issue (clear defect), warning (risky but not broken), opportunity (proactive improvement, no defect present)
title, severity (critical/high/medium/low)
evidence — mandatory, non-empty, and specific: name the exact URL/page inspected and the exact observation (a status code, an absent tag, a quoted structural detail, a link target). A finding with vague evidence ("navigation seems unclear") is not valid — retest and get a specific observation, or do not report the finding.
suggested_action — { summary, steps, priority }:
summary — one-line description of the fix.
steps — mandatory, 2-4 concrete, mechanism-specific actions explaining how to implement the fix and why it resolves the root cause (not just what to change). E.g. not "fix the broken link" but "replace the /a1.htm target with either (a) a working per-item detail page, or (b) remove the link and keep the item as plain text if no detail page is planned — a link is worse than no link if it 404s, since it signals neglect and erodes trust for every visitor who tries it."
priority — critical/high/medium/low.
Mandatory requirements (apply to every check)
Every finding must include evidence as defined above. No finding may be emitted without a specific, traceable observation backing it.
Every check must consider a proactive suggestion even when it finds no defect. If a check completes with zero issue/warning findings, evaluate whether a genuine, non-generic opportunity suggestion applies given what was actually observed on this site (not a boilerplate suggestion copied across every site). If nothing site-specific and non-obvious applies, it is acceptable to emit none for that check — but this must be a deliberate conclusion, not a skipped step.
Every suggested_action must include mechanism-specific steps, not only a summary. A one-line summary alone is insufficient for any finding, regardless of severity.
Evidence and false-positive rules
Never infer a defect from visual or semantic assumptions that cannot be verified with this skill's actual tool access (static HTML/HTTP only — no rendering).
Do not report a finding when the required evidence cannot be obtained.
Distinguish "not detected" from "confirmed absent" — if a signal simply wasn't found within the crawl/parse scope, that is not the same as verifying it doesn't exist anywhere on the site.
If a check cannot be reliably performed with the available tools (e.g. tap-target sizing, which needs rendering), mark it as unverified in the output rather than inventing evidence or silently skipping it without explanation.
Procedure
Check 1 — Findability from homepage (nav-driven)
Fetch site_url and identify the primary navigation menu.
Identify the offerings/categories the homepage itself highlights (headings, featured sections, prominent links/icons).
Cross-check: does every homepage-highlighted offering have a corresponding top-level nav entry? A category buried one submenu level deeper than a visitor would expect for something homepage-prominent still counts as a finding (see tested example below) — check both the top-level nav AND one level of submenu depth before concluding an offering is well-represented.
Assess whether each top-level nav label clearly indicates its contents (flag vague labels with no supporting context).
Follow 2-3 nav items and confirm each leads to a real, substantive page (cross-reference with Check 3's content-emptiness test).
If no nav/findability defect is found, consider a proactive suggestion — e.g. a genuinely useful category grouping or nav enhancement specific to what this site actually offers, not a generic template suggestion.
Severity: Critical — offering has no nav path at all, even one level deep. High — nav item leads to a broken/empty page. Medium — offering exists but only reachable via an unlabeled submenu, or nav label is vague.

Check 2 — Orientation on deep entry
For each page in entry_pages, fetch it directly, as if a visitor arrived via an external link rather than the homepage.
Check for orientation cues: breadcrumbs, a visible parent-category link, or any "you are here" signal.
Check standalone content completeness: does the page's own text explain what it is, without requiring prior context from the homepage?
Check for a clear next step: a CTA, related-content links, or an obvious path to browse further from this page.
If orientation is otherwise fine, consider a proactive suggestion — e.g. referral-aware content (referencing what an assistant likely told the visitor) as a strengthening opportunity, not a defect.
Severity: Critical — no orientation cues AND content doesn't explain itself. High — missing orientation cues, content otherwise self-explanatory. Medium — orientation exists, but no clear next step.

Check 3 — Broken links & dead-end pages
This check owns one question: can a visitor who lands on this page continue somewhere useful? Sitemap-based orphan-page detection is intentionally out of scope here — that's a crawlability/discoverability concern (does a crawler find the page at all), owned by another skill in this marketplace, not an engagement concern (can a visitor act once they're already on the page).

Starting from site_url, crawl a bounded sample of internal pages (homepage + top-level nav destinations + their direct children, capped at ~20-30 pages, respecting robots.txt).
For every internal link discovered, record its target URL and HTTP status.
Flag any link returning 4xx/5xx as a broken internal link.
For each crawled page, check BOTH: does it have outlinks beyond the global nav/footer, AND does it have substantive unique content? Failing both = dead-end page (loads fine, but gives the visitor nothing).
If no broken links/dead-ends are found, consider a proactive suggestion — e.g. adding related-content links between pages that are currently reachable but only loosely connected.
Severity: Critical — broken/dead-end reached from homepage or a prominent CTA. High — same, but from a secondary page.

Known limitation: some sites return 4xx to automated, non-browser clients on specific paths as an anti-bot measure, even though the page works normally for real visitors. This check cannot reliably distinguish that from a genuine defect without a full browser (out of scope for this skill's declared tools) — treat single-source broken-link findings on well-known, high-traffic domains with appropriate skepticism.

Check 4 — Mobile usability (static signals only)
This check relies only on static HTML/HTTP inspection — no browser rendering is available to this skill's declared tools.

Check that a <meta name="viewport" ...> tag is present in the page <head>.
Check for fixed-width elements in inline styles or CSS (e.g. width: 900px or similar) that exceed a typical mobile viewport width (~375- 414px) — this is a concrete, static signal of likely non-responsive layout, in place of any check that would require actually rendering the page.
Do not assess tap-target size or spacing — this requires a rendered layout and is out of scope for this skill's current tool access. If a rendering tool becomes available, this can be added as a further sub-check.
Severity: Critical — no viewport meta tag at all. Medium — viewport present but fixed-width elements exceeding mobile width are detected.

Check 5 — Page load performance (measurable observations only)
Measure HTTP response time for the initial page request.
Measure the HTML payload size (bytes) of the response.
Count synchronous <script> and <link rel="stylesheet"> tags present in <head> before the first content element — a static proxy for render-blocking risk, since actual render-blocking behavior requires a browser to confirm.
Where resource sizes are available from response headers, flag unusually large image resources.
Severity: Critical — response time far exceeds a reasonable reference threshold (e.g. multiple seconds) AND large payload/many blocking resources are also present. High — response time alone exceeds the threshold. Medium — payload size or blocking-resource count is high but response time is otherwise acceptable.

Evidence must be numeric and specific, e.g. "/home returned in 4.8s and contains 17 synchronous <script>/<link> tags in <head>" — not a vague statement like "page seems slow."

Check 6 — Site search quality
Detect whether an on-site search feature exists (a search input element, a role="search" region, or a dedicated search endpoint referenced in the page).
If a search endpoint can be identified and safely queried using a non-authenticated, read-only GET request (i.e. not submitting a form with side effects), run a plausible, relevant test query and assess whether results are relevant, empty, or erroring.
If no such safe, read-only query path can be identified, report only the presence/absence of a search feature — do not fabricate or assume search-quality results without actually querying it.
If absent on a large/multi-category site, note as an opportunity (not a defect) — many small sites reasonably don't need search.
Severity: High — search exists and a safe query returns irrelevant/no results for a clearly relevant query. Medium/Opportunity — no search on a site where content volume would benefit from one, or presence/absence only could be determined (no safe query path available).

Notes on maturity of checks
All checks have been designed against the reasoning in the Round 2 appendix. Some have been validated against real sites during development; see references/examples.md for illustrative evidence and output-format examples drawn from that testing.

Output
Before emitting the report, confirm for every finding:

 Evidence is specific and traceable (URL + exact observation).
 suggested_action.steps gives mechanism-specific fix guidance, not just a one-line summary.
 Each check has been evaluated for a proactive opportunity even where no defect was found (see step-level notes above).
Do not modify the site or submit any forms with real data — all checks are read-only (fetch and inspect only).