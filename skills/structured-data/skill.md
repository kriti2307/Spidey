---
name: structured-data-audit
description: >
  Audits a website's Schema.org/JSON-LD structured data for technical
  validity, semantic correctness, and consistency/trust, whether the
  machine-readable representation of the page is valid, appropriately
  typed, internally consistent, consistent with what a human visitor sees,
  and able to clearly identify the correct entity (vs. mistaken identity
  with unrelated namesakes). Use when diagnosing why an AI assistant might
  misrepresent, distrust, or fail to extract facts about a brand, as
  distinct from why the page couldn't be crawled/rendered at all, or why
  facts are stale/uncorroborated across the wider web.
license: MIT
allowed-tools: ["web_fetch", "http_get"]
---

# Structured Data Audit

## When to use

Use this skill once a target page's HTML is available (ideally post-render,
handed off from the crawl-render-audit skill, so JS-injected JSON-LD isn't
missed). This skill evaluates the JSON-LD structured data on that page: is
it present, valid, correctly typed, internally consistent, consistent with
the visible content, and does it clearly identify the entity it describes.

Do not use this skill to evaluate crawlability/JS-rendering (crawl-render-
audit), fact freshness or cross-web corroboration/NAP consistency
(freshness-corroboration), or on-site navigation/orientation
(engagement-audit). Structured data that references an entity is this
skill's concern; whether that entity is described consistently *elsewhere
on the web* is not.

## Inputs

- `html` (required): the page's HTML, ideally post-render.
- `url` (required): the page URL, for evidence traceability.

## Procedure

Checks fall into three groups — run all of them per page:

**Technical** (does the structured data parse and follow the spec at all)
1. No structured data present at all — SD001
2. Invalid/malformed JSON-LD — SD002
3. Missing `@context` — SD003
4. Missing `@type` — SD004

**Semantic** (is the structured data the *right* structured data)
5. Schema type doesn't match strong page-content signals — SD007
6. Missing important properties for the declared type — SD008
7. Entity has no disambiguating identifier (`sameAs`/`@id`) — SD009
8. Duplicate/conflicting `@id` across entities on the page — SD010

**Consistency / trust** (does the structured data agree — with itself, and
with what a human sees)
9. Schema value contradicts visible page content — SD006
10. Conflicting values across multiple JSON-LD blocks on the same page —
    SD005

See `references/structured-data-checklist.md` for the full detection logic,
thresholds, and false-positive guardrails behind each check.

## Severity guide

- **High** — no structured data at all; invalid JSON-LD; conflicting values
  (SD005/SD006) — these actively mislead or block machine extraction.
- **Medium** — missing `@context`/`@type`; wrong/missing type; missing
  properties; entity ambiguity; duplicate `@id`.
- Heuristic-based checks (schema-type mismatch, content mismatch) note
  their basis explicitly in evidence text so a human can sanity-check
  before acting — false positives are worse than a missed finding here.

## Output

Emit findings matching the shared marketplace schema: `id`, `title`,
`severity`, `evidence`, `suggested_action` (`summary`, `priority`, and
`steps` where a multi-step fix is needed). Read-only — this skill never
edits the site. See `references/example-findings.md` for format/severity
calibration examples.