# Spidey

**An Agent Skill Marketplace for AI-Discoverability & On-Site Engagement Audits**
---

## 1. What Spidey Is

Spidey is an [agentskills.io](https://agentskills.io)-format Agent Skill
Marketplace. Point it at a website, and it audits how well that site can
be **found and correctly understood by AI assistants**, and how well it
**keeps a human visitor engaged** once they arrive — then produces a
single structured report of findings and prioritized, actionable fixes.

It is a general-purpose auditor, not a checklist tuned to any specific
site. Every check encodes a *mechanism* (why an AI assistant or a visitor
would actually fail here), so the same skills generalize to sites they've
never seen before.

## 2. The Problem It Solves

Two failure modes look similar from the outside — "this brand doesn't show
up in AI answers, or shows up wrong" — but have different root causes:

- **AI discoverability** — a crawler/agent can't reach the page, can't
  parse what's on it, can't extract a clean fact from it, or gets
  conflicting/stale information depending on which part of the site (or
  which representation of the same page) it happens to read.
- **On-site engagement** — a visitor *does* land on the page (often deep,
  via an AI assistant's answer, not the homepage) and bounces because the
  page doesn't orient them, has dead ends, or doesn't give them a next
  step.

Spidey's skills are organized around these two halves of the problem, per
the Round 3 brief.

## 3. Architecture / Skill Composition

Spidey follows the marketplace convention: a `marketplace.json` manifest
lists every skill and designates exactly one **entrypoint**, which
composes the others' output into the final report. Each skill is a
self-contained, agentskills.io-compliant folder (`SKILL.md` +
`references/` + `scripts/`) that can, in principle, be reasoned about and
run independently — genuine separation of concerns, not one monolithic
checklist split arbitrarily.

```
spidey/
├── marketplace.json
├── README.md
├── shared/                    # common code shared across skills
└── skills/
    ├── audit-orchestrator/    # entrypoint
    ├── crawlability/
    ├── engagement-audit/
    ├── freshness/
    ├── non-text/
    └── structured-data/
```

## 4. What Each Skill Does

**crawlability**
Whether an agent can reach and read the page at all: `robots.txt`
compliance, HTTP status/redirect handling, and gaps between raw HTML and
the JS-rendered DOM (content that only exists after client-side
rendering).

**structured-data**
JSON-LD/Schema.org: presence and validity, correct/appropriate `@type`,
missing recommended properties, entity disambiguation (`sameAs`/`@id`),
and internal contradictions — schema vs. schema, and schema vs. the
page's own visible content.

**non-text**
Information locked in a non-text form with no text equivalent:
images/alt text, PDFs (including scanned/image-based PDFs, via OCR where
needed), inline SVG, CSS background-images, and audio/video (native
`<audio>`/`<video>` and iframe embeds like YouTube/Vimeo).

**freshness**
Whether time-sensitive facts are still true and consistent: expired
deadlines/events still presented as live, stale self-declared facts,
structured-data-vs-visible-content date conflicts, contradictions across
genuinely different sources describing the same fact, sitemap `lastmod`
plausibility, and (when a prior snapshot is available) whether a
freshness claim is backed by an actual content change or is a cosmetic
date bump.

**engagement-audit**
Whether a visitor who lands on the site — including a deep entry point an
AI assistant might link directly — can find what they came for, orient
themselves without a homepage visit, and reach a working next step:
findability from the homepage, deep-entry orientation, broken
links/dead-end/orphan pages, mobile usability, page performance, basic
accessibility, and site search quality.

**audit-orchestrator**
The entrypoint. Runs (or composes the output of) the specialist skills
above and assembles their findings into one final audit report.

Each skill's `SKILL.md` covers its inputs, procedure, and severity guide;
`references/` holds the full detection logic, thresholds, and
false-positive guardrails behind each check; example findings are
provided for format/severity calibration. None of the checks fire on
"existence" alone (a PDF, an old date, an image) — each requires a
specific, evidence-backed reason to believe something is actually broken.

## 5. How the Entrypoint Works

`skills/audit-orchestrator/` is the designated entrypoint in
`marketplace.json`. Its `scripts/orchestrator.py` runs the audit pipeline
across the specialist skills and hands the combined findings to
`scripts/report_renderer.py`, which renders the final report.

## 6. How to Run the Audit

Invoke the orchestrator entrypoint, pointing it at the target site:

```bash
python skills/audit-orchestrator/scripts/orchestrator.py <target-url>
```

See `orchestrator.py` for the exact accepted arguments/options.

## 7. Expected Outputs

Running the orchestrator produces two outputs, generated by
`report_renderer.py`:

- **A canonical JSON report** — machine-readable, following the shared
  finding schema (`site`, `audited_at`, a severity-count `summary`, and a
  `findings` array where each finding has `id`, `title`, `severity`,
  `evidence`, and `suggested_action`).
- **A human-readable Markdown report** — `audit-report.md`, written
  alongside the orchestrator's scripts
  (`skills/audit-orchestrator/scripts/audit-report.md`) — summarizing the
  same findings for a non-expert to read and act on directly.

## 8. Guardrails

- **Recommend-only.** No skill modifies a live website. Every check is
  read-only: fetch and inspect, never write.
- **Respects `robots.txt`** before fetching any page, PDF, or image.
- **No destructive, authenticated, or rate-abusing actions.** No forms are
  submitted with real data; no login-gated content is accessed.
- Checks that are inherently uncertain from static analysis alone
  (heuristic type-matching, background-image classification, OCR
  relevance, snapshot size-delta significance) are explicitly marked with
  a confidence level in their evidence, rather than asserted as confirmed
  defects — false positives are treated as more costly than a missed
  finding.

## 9. Setup / Dependencies

Different skills use whichever runtime best fits their concern rather
than a single forced stack — e.g. Python for HTML/data-centric checks
(structured-data, non-text, freshness), with headless-browser rendering
in **crawlability** handling JS-rendering gaps. Each skill declares its
own tool needs in its `SKILL.md` frontmatter (`allowed-tools`); see a
given skill's `scripts/` for its specific package dependencies. Optional
functionality (e.g. OCR in `non-text`) degrades gracefully and reports its
own unavailability rather than failing the whole audit when a dependency
isn't present in the running environment.

## 10. Generalization Focus

No example sites were used to build these checks into a fixed list of
site-specific fixes — every check is derived from a general mechanism
(how crawlers read pages, how AI assistants source and corroborate facts,
how structured data is consumed, why visitors disengage) documented in
each skill's `references/` folder, so the same checks apply to any site,
not just the ones used during development and testing.